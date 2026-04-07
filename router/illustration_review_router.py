from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models import schemas, models
from utils.database import get_db
from utils.auth import get_current_user
from utils.story_access import get_owned_story_or_404
from utils.response import success, error
from agent.illustration_reviewer import IllustrationReviewerAgent
from typing import List, Dict, Any


def _to_plain_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()  # Pydantic v2
    if hasattr(value, "dict"):
        return value.dict()  # Pydantic v1
    return {}

router = APIRouter(prefix="/illustration-review", tags=["插画审核中心 (Illustration Review)"])


@router.post("/review", summary="插画科学审核与人物一致性检查")
def review_illustrations(
    req: schemas.IllustrationReviewRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    对生成的插画进行全面审核：
    - **story_id**: 库中关联记录ID
    - **scenes**: 插画分镜列表（支持image_url进行视觉分析）
    - **character_config**: 人物设定配置（可选）

    审核内容包括：
    1. 科学准确性审核（支持图片视觉分析）
    2. 人物一致性检查（外貌、服装、风格等）
    3. 不合逻辑画面检测（物理规律、比例尺寸、场景矛盾等）
    4. 综合审核结论
    """
    try:
        agent = IllustrationReviewerAgent()

        # 从story_id获取目标受众信息
        target_audience = "大众"
        if req.story_id:
            story = get_owned_story_or_404(db, req.story_id, current_user.id)
            if story:
                target_audience = story.target_audience or "大众"

        # 确保 scenes 不为空
        scenes = req.scenes or []
        if not scenes:
            return error(code=400, msg="没有可审核的插画场景")

        scenes_plain = [_to_plain_dict(scene) for scene in scenes]
        character_config_plain = _to_plain_dict(req.character_config) if req.character_config else None

        review_result = agent.review_all_scenes(
            scenes=scenes_plain,
            target_audience=target_audience,
            character_config=character_config_plain,
        )

        # 存储反馈记录
        try:
            feedback = models.AgentFeedback(
                user_id=current_user.id,
                story_id=req.story_id,
                agent_type="illustration_reviewer",
                feedback=str(review_result)
            )
            db.add(feedback)
            db.commit()
        except Exception as db_error:
            print(f"[数据库记录失败] {db_error}")
            # 即使数据库记录失败，也返回审核结果
            pass

        return success(review_result, msg="插画审核完成")

    except Exception as e:
        print(f"[插画审核异常] {str(e)}")
        import traceback
        traceback.print_exc()
        return error(code=500, msg=f"插画审核失败: {str(e)}")
