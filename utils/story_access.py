from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import models


def get_owned_story_or_404(db: Session, story_id: int, user_id: int) -> models.Story:
    story = (
        db.query(models.Story)
        .filter(models.Story.id == story_id)
        .filter(models.Story.user_id == user_id)
        .first()
    )
    if not story:
        raise HTTPException(status_code=404, detail="故事不存在或无权访问")
    return story
