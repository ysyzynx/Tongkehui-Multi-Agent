from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models import schemas, models
from utils.database import get_db
from utils.auth import get_current_user
from utils.story_access import get_owned_story_or_404
from utils.response import success
from agent.literature_checker import LiteratureCheckerAgent

router = APIRouter(prefix="/literature", tags=["文学审核中心 (Literature Checker)"])


@router.post("/review", summary="文学性审核与润色")
def review_story(
    req: schemas.LiteratureReviewRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    对故事进行文学性审查并输出润色版本：
    - **story_id**: 库中关联记录ID
    - **title**: 故事标题
    - **content**: 待审查正文
    - **target_audience**: 目标受众群体（可选）
    - **age_group**: 年龄段（可选）
    """
    get_owned_story_or_404(db, req.story_id, current_user.id)

    agent = LiteratureCheckerAgent()
    review_result = agent.review_story(
        title=req.title,
        content=req.content,
        target_audience=req.target_audience,
        age_group=req.age_group,
    )

    feedback = models.AgentFeedback(
        user_id=current_user.id,
        story_id=req.story_id,
        agent_type="literature_checker",
        feedback=str(review_result)
    )
    db.add(feedback)
    db.commit()

    return success(review_result, msg="文学审核完成")
