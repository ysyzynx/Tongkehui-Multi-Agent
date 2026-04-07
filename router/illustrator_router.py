from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models import schemas, models
from utils.database import get_db
from utils.auth import get_current_user
from utils.story_access import get_owned_story_or_404
from utils.response import success, error
from agent.illustrator import IllustratorAgent

router = APIRouter(prefix="/illustrator", tags=["插画建议中心 (Illustrator)"])

@router.post("/suggest", summary="生成配图建议 (Prompt)")
def suggest_illustrations(
    req: schemas.IllustratorRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    解析故事本，提取核心场景转化为插画Prompts：
    - **story_id**: 库中关联记录ID
    - **content**: 待配图故事
    - **image_count**: 分镜数量
    - **art_style**: 画风要求
    - **extra_requirements**: 额外绘画要求
    """
    get_owned_story_or_404(db, req.story_id, current_user.id)

    agent = IllustratorAgent()
    suggestions = agent.run(
        story_content=req.content,
        image_count=req.image_count or 4,
        art_style=req.art_style or "卡通",
        extra_requirements=req.extra_requirements or "",
    )

    if isinstance(suggestions, dict) and "error" in suggestions:
        return error(code=500, msg="插画生成失败", data=suggestions)
    
    # 存储反馈记录
    feedback = models.AgentFeedback(
        user_id=current_user.id,
        story_id=req.story_id,
        agent_type="illustrator",
        feedback=str(suggestions)
    )
    db.add(feedback)
    db.commit()
    
    return success({"scenes": suggestions}, msg="插画建议提取完成")


@router.post("/regenerate", summary="根据用户意见重绘单张图片")
def regenerate_illustration(
    req: schemas.IllustratorRegenerateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    根据用户对某一分镜图片的修改意见，重新生成该分镜图。
    """
    get_owned_story_or_404(db, req.story_id, current_user.id)

    agent = IllustratorAgent()
    regenerated = agent.regenerate_image(
        image_prompt=req.image_prompt,
        feedback=req.feedback,
        art_style=req.art_style or "卡通",
        extra_requirements=req.extra_requirements or "",
    )

    if isinstance(regenerated, dict) and "error" in regenerated:
        return error(code=500, msg="分镜重绘失败", data=regenerated)

    feedback = models.AgentFeedback(
        user_id=current_user.id,
        story_id=req.story_id,
        agent_type="illustrator_regenerate",
        feedback=str({
            "scene_id": req.scene_id,
            "feedback": req.feedback,
            "result": regenerated,
        })
    )
    db.add(feedback)
    db.commit()

    return success({
        "scene_id": req.scene_id,
        "image_prompt": regenerated.get("image_prompt", req.image_prompt),
        "image_url": regenerated.get("image_url", ""),
    }, msg="分镜重绘完成")
