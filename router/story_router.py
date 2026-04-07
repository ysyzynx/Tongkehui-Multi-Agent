from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
import time
import logging
from models import schemas, models
from utils.database import get_db
from utils.response import success, error
from utils.llm_client import llm_client
from utils.auth import get_current_user
from agent.story_creator import StoryCreatorAgent

router = APIRouter(prefix="/story", tags=["创作中心 (Story Creator)"])
logger = logging.getLogger("tongkehui.story")


@router.post("/suggest-titles", summary="根据主题生成4条标题建议")
def suggest_titles(req: schemas.StorySuggestTitlesRequest):
    theme = (req.theme or "").strip()
    if len(theme) < 2:
        return error(code=400, msg="主题至少需要2个字符")

    agent = StoryCreatorAgent()
    generated = agent.suggest_titles(
        theme=theme,
        target_audience=req.target_audience,
        age_group=req.age_group,
    )

    suggestions = generated.get("suggestions", []) if isinstance(generated, dict) else []
    return success({"suggestions": suggestions}, msg="标题建议生成成功")

@router.post("/create", summary="提交创作参数并生成科普故事")
def create_story(
    req: schemas.StoryCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    提交用户设定进行科普故事的创作，返回故事内容及ID。
    - **theme**: 选题关键词 (如: 宇宙黑洞)
    - **age_group**: 受众群体 (如: 6-8岁)
    - **style**: 文章风格 (如: 趣味、冒险、科幻)
    - **use_rag**: 是否使用知识库检索增强（默认开启）
    - **rag_doc_type**: RAG知识库类型（SCIENCE_FACT=科学事实/FACT=通用）
    - **selected_rag_ids**: 用户选中的知识库文档ID列表（仅使用这些文档）
    """
    try:
        # 1. 实例化智能体并运行
        agent = StoryCreatorAgent()
        use_fact_rag = req.use_fact_rag if req.use_fact_rag is not None else req.use_rag
        generated = agent.run(
            project_title=req.project_title,
            theme=req.theme,
            age_group=req.age_group,
            style=req.style,
            target_audience=req.target_audience,
            extra_requirements=req.extra_requirements,
            word_count=req.word_count,
            db=db,
            use_rag=use_fact_rag if use_fact_rag is not None else True,
            use_deepsearch=req.use_deepsearch if req.use_deepsearch is not None else False,
            deepsearch_top_k=req.deepsearch_top_k or 6,
            rag_doc_type=req.rag_doc_type or "SCIENCE_FACT",
            rag_top_k=req.rag_top_k or 4,
            selected_rag_ids=req.selected_rag_ids,
        )

        if not isinstance(generated, dict):
            generated = {
                "title": req.project_title or "未命名故事",
                "content": "内容生成过程中出现异常，请稍后重试。",
                "glossary": [],
                "rag_enabled": False,
            }

        # 2. 将入参保存到数据库 (后续可更新内容)
        db_story = models.Story(
            user_id=current_user.id,
            theme=req.theme or req.project_title or "未命名主题",
            age_group=req.age_group or "全年龄段",
            style=req.style,
            target_audience=req.target_audience,
            extra_requirements=req.extra_requirements,
            content=generated.get("content", ""),
            glossary=str(generated.get("glossary", [])),
            status=1
        )

        # SQLite 在多进程/热重载场景下可能偶发写入失败，做有限重试
        last_db_error = None
        for attempt in range(3):
            try:
                db.add(db_story)
                db.commit()
                db.refresh(db_story)
                last_db_error = None
                break
            except OperationalError as oe:
                db.rollback()
                last_db_error = oe
                time.sleep(0.2 * (attempt + 1))
            except Exception as ex:
                db.rollback()
                last_db_error = ex
                break

        if last_db_error is not None:
            logger.exception("Story persisted failed but generation succeeded: %s", last_db_error)

        # 3. 返回前端统一格式
        llm_runtime = llm_client.get_runtime_config()

        response_data = {
            "id": getattr(db_story, "id", None),
            "title": generated.get("title", ""),
            "content": generated.get("content", ""),
            "glossary": generated.get("glossary", []),
            "rag_enabled": generated.get("rag_enabled", False),
            "llm_provider": llm_runtime.get("provider", "custom"),
            "llm_provider_label": llm_runtime.get("provider_label", "通义千问"),
        }
        # 若使用了RAG，返回使用的证据（方便调试和前端展示）
        if generated.get("rag_evidence_used"):
            response_data["rag_evidence_used"] = generated.get("rag_evidence_used")

        if last_db_error is not None:
            response_data["persist_warning"] = f"生成成功，但保存记录失败: {str(last_db_error)}"
            return success(response_data, msg="故事生成成功（保存记录失败）")

        return success(response_data, msg="故事生成成功")

    except Exception as ex:
        db.rollback()
        return error(code=500, msg=f"故事生成失败: {str(ex)}")
