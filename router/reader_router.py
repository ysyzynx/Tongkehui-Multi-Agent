from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models import schemas, models
from utils.database import get_db
from utils.auth import get_current_user
from utils.story_access import get_owned_story_or_404
from utils.response import success
from agent.reader import ReaderAgent

router = APIRouter(prefix="/reader", tags=["读者评分中心 (Reader)"])


def _normalize_reader_result(result: dict) -> dict:
    if not isinstance(result, dict):
        result = {}

    feedback_text = (
        str(result.get("reader_feedback") or "").strip()
        or str(result.get("audience_feedback") or "").strip()
        or str(result.get("feedback") or "").strip()
        or str(result.get("comment") or "").strip()
    )

    fallback_content = str(result.get("content") or "").strip()
    if not feedback_text and fallback_content and "内容生成过程中出现异常" not in fallback_content:
        feedback_text = fallback_content

    if not feedback_text:
        err = str(result.get("error") or "").strip()
        feedback_text = f"观众反馈生成异常：{err}" if err else "暂无反馈内容"

    normalized = dict(result)
    normalized["reader_feedback"] = feedback_text
    return normalized

@router.post("/evaluate", summary="模拟目标受众打分与反馈")
def evaluate_story(
    req: schemas.ReaderRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    虚拟读者对文本的接受程度、吸引力和易读性打分：
    - **story_id**: 库中关联记录ID
    - **title**: 故事标题
    - **content**: 待评估文本
    - **target_audience**: 目标受众群体（可选，未传则回退 age_group）
    """
    get_owned_story_or_404(db, req.story_id, current_user.id)

    agent = ReaderAgent()
    target_audience = req.target_audience or req.age_group or "大众"
    eval_result = agent.run(
        story_content=req.content,
        title=req.title or "未命名故事",
        target_audience=target_audience,
    )
    eval_result = _normalize_reader_result(eval_result)
    
    # 存储反馈记录
    feedback = models.AgentFeedback(
        user_id=current_user.id,
        story_id=req.story_id,
        agent_type="reader",
        feedback=str(eval_result)
    )
    db.add(feedback)
    db.commit()
    
    return success(eval_result, msg="读者评估完成")


@router.post("/refine", summary="根据观众反馈微调正文（4.0）")
def refine_story_by_reader_feedback(
    req: schemas.ReaderRefineRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    基于科学审查后版本正文 + 观众反馈，进行轻量微调，产出 4.0 版本。
    """
    get_owned_story_or_404(db, req.story_id, current_user.id)

    agent = ReaderAgent()
    target_audience = req.target_audience or req.age_group or "大众"
    refine_result = agent.refine_by_feedback(
        story_content=req.content,
        title=req.title or "未命名故事",
        target_audience=target_audience,
        reader_feedback=req.feedback,
    )

    feedback = models.AgentFeedback(
        user_id=current_user.id,
        story_id=req.story_id,
        agent_type="reader_refine",
        feedback=str(refine_result)
    )
    db.add(feedback)
    db.commit()

    return success(refine_result, msg="观众反馈微调完成")
