from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import schemas, models
from utils.database import get_db
from utils.fact_rag import search_fact_evidence
from utils.deepsearch_client import deepsearch_client
from utils.llm_client import llm_client
from utils.auth import get_current_user
from utils.story_access import get_owned_story_or_404
from utils.response import success
from agent.science_checker import ScienceCheckerAgent
from agent.self_feedback_science_checker import SelfFeedbackScienceChecker
import traceback
import json

router = APIRouter(prefix="/check", tags=["科学审核中心 (Science Checker)"])

@router.post("/verify", summary="科学审核与事实校验")
def verify_story(
    req: schemas.CheckRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    提交生成的文本进行科学性审核：
    - **story_id**: 库中关联记录ID
    - **content**: 待审核文本
    """
    try:
        get_owned_story_or_404(db, req.story_id, current_user.id)

        evidence_items = []
        deepsearch_context = {}
        debug_info = {
            "use_deepsearch": req.use_deepsearch,
            "use_fact_rag": req.use_fact_rag,
            "rag_doc_type": req.rag_doc_type,
            "deepsearch_evidence_count": 0,
            "fact_rag_evidence_count": 0,
        }

        if req.use_deepsearch:
            deepsearch_context = deepsearch_client.search_science_context(
                title=req.title or "未命名故事",
                content=req.content,
                target_audience=req.target_audience or "大众",
                top_k=req.deepsearch_top_k or 6,
            )
            deepsearch_evidence = deepsearch_context.get("evidence_used")
            if isinstance(deepsearch_evidence, list) and deepsearch_evidence:
                evidence_items.extend(deepsearch_evidence)
                debug_info["deepsearch_evidence_count"] = len(deepsearch_evidence)

        if req.use_fact_rag:
            query = f"{req.title or ''}\n{req.content[:1800]}".strip()
            fact_evidence = search_fact_evidence(
                db,
                query=query,
                top_k=req.evidence_top_k or 6,
                doc_type=req.rag_doc_type or "SCIENCE_FACT"
            )
            if isinstance(fact_evidence, list):
                evidence_items.extend(fact_evidence)
                debug_info["fact_rag_evidence_count"] = len(fact_evidence)

        # 1. 调用审核智能体
        agent = ScienceCheckerAgent()
        check_result = agent.run(
            story_title=req.title or "未命名故事",
            story_content=req.content,
            target_audience=req.target_audience or "大众",
            evidence_context=evidence_items,
            deepsearch_context=deepsearch_context,
        )

        # 添加调试信息到结果
        check_result["_debug"] = debug_info

        # 2. 存储反馈记录
        feedback = models.AgentFeedback(
            user_id=current_user.id,
            story_id=req.story_id,
            agent_type="science_checker",
            feedback=str(check_result)
        )
        db.add(feedback)
        db.commit()

        return success(check_result, msg="科学审核完成")
    except Exception as e:
        db.rollback()
        error_detail = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        raise HTTPException(status_code=500, detail=error_detail)


@router.post("/verify-self-feedback", summary="自反馈科学审核（OpenScholar 技术）")
def verify_story_self_feedback(
    req: schemas.CheckRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    使用自反馈迭代机制进行科学审核（基于 OpenScholar 论文）：
    - **story_id**: 库中关联记录ID
    - **content**: 待审核文本
    - **use_deepsearch**: 是否使用 DeepSearch
    - **use_fact_rag**: 是否使用事实 RAG 检索

    工作流程：
    1. 初始审核：发现问题，生成检索查询
    2. 补充检索：基于查询搜索证据
    3. 反馈生成：基于证据生成修改建议
    4. 迭代优化：应用反馈修改文章（最多3轮）
    5. 引用验证：确保每个论断都有支撑
    """
    try:
        get_owned_story_or_404(db, req.story_id, current_user.id)

        evidence_items = []
        deepsearch_context = {}
        debug_info = {
            "use_deepsearch": req.use_deepsearch,
            "use_fact_rag": req.use_fact_rag,
            "use_hybrid_retriever": False,  # 暂时禁用，确保稳定性
            "use_citation_verifier": False,  # 暂时禁用，确保稳定性
            "rag_doc_type": req.rag_doc_type,
            "deepsearch_evidence_count": 0,
            "fact_rag_evidence_count": 0,
            "workflow": "self-feedback-iterative",
        }

        if req.use_deepsearch:
            deepsearch_context = deepsearch_client.search_science_context(
                title=req.title or "未命名故事",
                content=req.content,
                target_audience=req.target_audience or "大众",
                top_k=req.deepsearch_top_k or 6,
            )
            deepsearch_evidence = deepsearch_context.get("evidence_used")
            if isinstance(deepsearch_evidence, list) and deepsearch_evidence:
                evidence_items.extend(deepsearch_evidence)
                debug_info["deepsearch_evidence_count"] = len(deepsearch_evidence)

        if req.use_fact_rag:
            query = f"{req.title or ''}\n{req.content[:1800]}".strip()
            fact_evidence = search_fact_evidence(
                db,
                query=query,
                top_k=req.evidence_top_k or 6,
                doc_type=req.rag_doc_type or "SCIENCE_FACT"
            )
            if isinstance(fact_evidence, list):
                evidence_items.extend(fact_evidence)
                debug_info["fact_rag_evidence_count"] = len(fact_evidence)

        # 调用自反馈审核智能体（暂时禁用新组件确保稳定性）
        agent = SelfFeedbackScienceChecker(
            db_session=db,
            use_hybrid_retrieval=False,
            use_citation_verifier=False
        )
        check_result = agent.run(
            story_title=req.title or "未命名故事",
            story_content=req.content,
            target_audience=req.target_audience or "大众",
            evidence_context=evidence_items,
            deepsearch_context=deepsearch_context,
            topic=req.title,
        )

        # 添加调试信息到结果
        check_result["_debug"] = debug_info
        check_result["_iteration_history"] = agent.iteration_history

        # 存储反馈记录
        feedback = models.AgentFeedback(
            user_id=current_user.id,
            story_id=req.story_id,
            agent_type="science_checker_self_feedback",
            feedback=str(check_result)
        )
        db.add(feedback)
        db.commit()

        return success(check_result, msg="自反馈科学审核完成")
    except Exception as e:
        db.rollback()
        error_detail = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        raise HTTPException(status_code=500, detail=error_detail)


@router.post("/apply-selected", summary="根据用户采纳项生成科学修订版本")
def apply_selected_science_suggestions(
    req: schemas.ScienceApplySelectedRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    仅根据用户明确采纳的科学建议生成修订稿：
    - 未采纳项不应进入修订正文
    - 无采纳项时返回原文
    """
    try:
        get_owned_story_or_404(db, req.story_id, current_user.id)

        selected_sections = req.selected_sections or []
        adopted_sections = [str(item.section).strip() for item in selected_sections if str(item.section).strip()]

        if not adopted_sections:
            payload = {
                "revised_content": req.content,
                "adopted_sections": [],
                "notes": "未采纳任何建议，沿用原文。",
            }
            feedback = models.AgentFeedback(
                user_id=current_user.id,
                story_id=req.story_id,
                agent_type="science_checker_apply_selected",
                feedback=str(payload),
            )
            db.add(feedback)
            db.commit()
            return success(payload, msg="未采纳建议，已保留原文")

        selected_payload = []
        for item in selected_sections:
            section_name = str(item.section or "").strip()
            if not section_name:
                continue
            selected_payload.append({
                "section": section_name,
                "suggestion": str(item.suggestion or "").strip(),
                "suggested_revision": str(item.suggested_revision or "").strip(),
                "issue_list": item.issue_list or [],
                "modification_list": item.modification_list or [],
            })

        system_prompt = "你是严谨的科学内容修订助手，只能按用户已采纳建议进行改写。"
        user_prompt = f"""
请仅根据“已采纳建议”对科普故事进行修订，并返回 JSON：
{{
  "revised_content": "string",
  "notes": "string"
}}

约束：
1) 只能落实用户已采纳项，未采纳内容不得新增。
2) 保持原文结构与叙事风格，避免无关改写。
3) 修订后应更科学严谨，表达仍适合目标读者。

目标读者：{req.target_audience or '大众'}
标题：{req.title or '未命名故事'}

原文：
{req.content}

已采纳建议（JSON）：
{json.dumps(selected_payload, ensure_ascii=False)}
""".strip()

        llm_result = llm_client.generate_json(system_prompt, user_prompt)
        revised_content = str(llm_result.get("revised_content") or "").strip() if isinstance(llm_result, dict) else ""
        notes = str(llm_result.get("notes") or "").strip() if isinstance(llm_result, dict) else ""

        if not revised_content:
            revised_content = req.content
            if not notes:
                notes = "模型未返回有效修订稿，已回退原文。"

        payload = {
            "revised_content": revised_content,
            "adopted_sections": adopted_sections,
            "notes": notes,
        }

        feedback = models.AgentFeedback(
            user_id=current_user.id,
            story_id=req.story_id,
            agent_type="science_checker_apply_selected",
            feedback=str(payload),
        )
        db.add(feedback)
        db.commit()

        return success(payload, msg="已根据采纳项生成科学修订版本")
    except Exception as e:
        db.rollback()
        error_detail = {
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
        raise HTTPException(status_code=500, detail=error_detail)
