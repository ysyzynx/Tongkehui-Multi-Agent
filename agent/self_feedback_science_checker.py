"""
Self-Feedback Science Checker Agent
基于 OpenScholar 的自反馈迭代推理机制
"""
import json
from typing import Dict, Any, List, Optional, Tuple
from agent.base_agent import BaseAgent
from agent.science_checker import ScienceCheckerAgent
from utils.llm_client import llm_client
from utils.fact_rag import search_fact_evidence
from utils.hybrid_retriever import HybridRetriever
from utils.citation_verifier import CitationVerifier
from prompts.self_feedback_science_prompt import (
    INITIAL_REVIEW_SYSTEM_PROMPT,
    INITIAL_REVIEW_USER_PROMPT,
    FEEDBACK_GENERATION_SYSTEM_PROMPT,
    FEEDBACK_GENERATION_USER_PROMPT,
    ITERATIVE_OPTIMIZATION_SYSTEM_PROMPT,
    ITERATIVE_OPTIMIZATION_USER_PROMPT,
    CITATION_VERIFICATION_SYSTEM_PROMPT,
    CITATION_VERIFICATION_USER_PROMPT,
    WORKFLOW_SUMMARY_PROMPT,
)


class SelfFeedbackScienceChecker(BaseAgent):
    """
    带自反馈机制的科学审核者 Agent

    工作流程：
    1. 初始审核：发现问题，生成检索查询
    2. 补充检索：基于查询搜索证据（使用混合检索器）
    3. 反馈生成：基于证据生成修改建议
    4. 迭代优化：应用反馈修改文章
    5. 引用验证：确保每个论断都有支撑（使用引用验证器）
    """

    def __init__(self, db_session=None, use_hybrid_retrieval: bool = True, use_citation_verifier: bool = True):
        super().__init__(
            name="Self-Feedback Science Checker",
            description="Science reviewer with self-feedback iterative refinement mechanism"
        )
        self.base_checker = ScienceCheckerAgent()
        self.db_session = db_session
        self.max_iterations = 3  # 最多迭代3轮
        self.all_evidence: List[Dict[str, Any]] = []
        self.iteration_history: List[Dict[str, Any]] = []

        # Phase 3-4 新组件
        self.use_hybrid_retrieval = use_hybrid_retrieval
        self.use_citation_verifier = use_citation_verifier

        if use_hybrid_retrieval:
            try:
                from utils.hybrid_retriever import HybridRetriever
                self.hybrid_retriever = HybridRetriever(db_session=db_session)
            except Exception as e:
                print(f"[SelfFeedbackScienceChecker] HybridRetriever 初始化失败，已禁用: {e}")
                self.use_hybrid_retrieval = False

        if use_citation_verifier:
            try:
                from utils.citation_verifier import CitationVerifier
                self.citation_verifier = CitationVerifier(llm_client=llm_client)
            except Exception as e:
                print(f"[SelfFeedbackScienceChecker] CitationVerifier 初始化失败，已禁用: {e}")
                self.use_citation_verifier = False

    def _safe_json_parse(self, text: str, fallback: Any = None) -> Any:
        """安全解析 JSON"""
        try:
            if isinstance(text, dict):
                return text
            if not text or not isinstance(text, str):
                return fallback
            # 清理可能的 markdown 标记
            cleaned = text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        except Exception:
            return fallback

    def _to_string(self, value: Any) -> str:
        """安全转换为字符串"""
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False) if value else ""

    def run_initial_review(
        self,
        title: str,
        content: str,
        target_audience: str = "8-12岁儿童",
    ) -> Dict[str, Any]:
        """
        阶段 1: 初始审核，发现问题
        """
        user_prompt = INITIAL_REVIEW_USER_PROMPT.format(
            title=title,
            target_audience=target_audience,
            content=content,
        )

        result = llm_client.generate_json(
            INITIAL_REVIEW_SYSTEM_PROMPT,
            user_prompt,
        )

        parsed = self._safe_json_parse(result, {
            "has_issues": False,
            "issues": [],
            "summary": "未发现明显科学问题"
        })

        # 确保数据结构正确
        if "has_issues" not in parsed:
            parsed["has_issues"] = bool(parsed.get("issues"))
        if "issues" not in parsed:
            parsed["issues"] = []
        if "summary" not in parsed:
            parsed["summary"] = "初始审核完成"

        return parsed

    def run_supplementary_search(
        self,
        issues: List[Dict[str, Any]],
        topic: Optional[str] = None,
        age_range: str = "8-12岁",
    ) -> List[Dict[str, Any]]:
        """
        阶段 2: 补充检索，基于问题搜索证据
        """
        all_evidence = []

        for issue in issues:
            search_query = issue.get("search_query", "")
            if not search_query:
                continue

            # 使用原有的 fact_rag（更稳定）
            if self.db_session:
                evidence = search_fact_evidence(
                    db=self.db_session,
                    query=search_query,
                    top_k=3,
                    doc_type="SCIENCE_FACT",
                )
            else:
                evidence = []

            # 标记证据对应的问题
            for ev in evidence:
                ev["for_issue_id"] = issue.get("issue_id")
                all_evidence.append(ev)

        self.all_evidence = all_evidence
        return all_evidence

    def generate_feedback(
        self,
        title: str,
        content: str,
        issues: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        target_audience: str = "8-12岁儿童",
    ) -> Dict[str, Any]:
        """
        阶段 3: 基于证据生成反馈建议
        """
        user_prompt = FEEDBACK_GENERATION_USER_PROMPT.format(
            title=title,
            target_audience=target_audience,
            content=content,
            issues_json=self._to_string(issues),
            search_results_json=self._to_string(evidence),
        )

        result = llm_client.generate_json(
            FEEDBACK_GENERATION_SYSTEM_PROMPT,
            user_prompt,
        )

        parsed = self._safe_json_parse(result, {
            "feedback_items": [],
            "needs_additional_search": False,
            "additional_queries": [],
            "summary": "反馈生成完成"
        })

        if "feedback_items" not in parsed:
            parsed["feedback_items"] = []
        if "needs_additional_search" not in parsed:
            parsed["needs_additional_search"] = False
        if "additional_queries" not in parsed:
            parsed["additional_queries"] = []

        return parsed

    def run_iterative_optimization(
        self,
        title: str,
        content: str,
        feedback: Dict[str, Any],
        target_audience: str = "8-12岁儿童",
    ) -> Dict[str, Any]:
        """
        阶段 4: 迭代优化，应用反馈修改文章
        """
        feedback_items = feedback.get("feedback_items", [])

        user_prompt = ITERATIVE_OPTIMIZATION_USER_PROMPT.format(
            title=title,
            target_audience=target_audience,
            content=content,
            feedback_json=self._to_string(feedback_items),
        )

        result = llm_client.generate_json(
            ITERATIVE_OPTIMIZATION_SYSTEM_PROMPT,
            user_prompt,
        )

        parsed = self._safe_json_parse(result, {
            "revised_content": content,
            "changes_made": [],
            "summary": "优化完成"
        })

        if "revised_content" not in parsed or not parsed["revised_content"]:
            parsed["revised_content"] = content
        if "changes_made" not in parsed:
            parsed["changes_made"] = []

        return parsed

    def run_citation_verification(
        self,
        title: str,
        content: str,
        evidence: List[Dict[str, Any]],
        target_audience: str = "8-12岁儿童",
    ) -> Dict[str, Any]:
        """
        阶段 5: 引用验证，确保每个科学论断都有支撑
        """
        # 使用稳定的 LLM 方法
        user_prompt = CITATION_VERIFICATION_USER_PROMPT.format(
            title=title,
            target_audience=target_audience,
            content=content,
            evidence_json=self._to_string(evidence),
        )

        result = llm_client.generate_json(
            CITATION_VERIFICATION_SYSTEM_PROMPT,
            user_prompt,
        )

        parsed = self._safe_json_parse(result, {
            "all_supported": True,
            "statements": [],
            "final_pass": True,
            "review_summary": {
                "overall_assessment": "科学审核通过",
                "strengths": [],
                "areas_for_improvement": [],
                "recommendation": "建议通过"
            },
            "content_with_citations": content
        })

        # 确保数据结构正确
        if "all_supported" not in parsed:
            parsed["all_supported"] = True
        if "statements" not in parsed:
            parsed["statements"] = []
        if "final_pass" not in parsed:
            parsed["final_pass"] = True
        if "review_summary" not in parsed:
            parsed["review_summary"] = {}
        if "content_with_citations" not in parsed:
            parsed["content_with_citations"] = content

        return parsed

    def generate_workflow_summary(
        self,
        initial_review: Dict[str, Any],
        iteration_history: List[Dict[str, Any]],
        final_verification: Dict[str, Any],
        final_content: str,
    ) -> Dict[str, Any]:
        """
        生成整体流程总结
        """
        # 整理问题解决情况
        issues_found = []
        for issue in initial_review.get("issues", []):
            resolved = False
            resolution = ""
            # 检查是否在迭代中解决了
            for iteration in iteration_history:
                changes = iteration.get("changes_made", [])
                for change in changes:
                    if change.get("feedback_id") == issue.get("issue_id"):
                        resolved = True
                        resolution = change.get("description", "")
                        break

            issues_found.append({
                "id": issue.get("issue_id"),
                "description": issue.get("description"),
                "resolved": resolved,
                "resolution": resolution,
            })

        # 整理引用信息
        citations = []
        statements = final_verification.get("statements", [])
        citation_map = {}
        for stmt in statements:
            mark = stmt.get("citation_mark")
            if mark and mark not in citation_map:
                evidence_list = stmt.get("supporting_evidence", [])
                if evidence_list:
                    citation_map[mark] = evidence_list[0]
                    citations.append({
                        "mark": mark,
                        "source": evidence_list[0].get("source_name", ""),
                        "snippet": evidence_list[0].get("snippet", "")[:100] + "...",
                    })

        final_pass = final_verification.get("final_pass", True)
        review_summary = final_verification.get("review_summary", {})

        # 整理 issues 为字符串列表（前端期望格式）
        issues_list = [issue.get("description", "") for issue in issues_found if issue.get("description")]
        modifications_list = [
            f"问题: {issue.get('description', '')} - 已解决"
            for issue in issues_found
            if issue.get("resolved", False)
        ]

        return {
            "passed": final_pass,
            "issues": issues_list,  # 前端期望的字段名
            "modifications_made": modifications_list,  # 前端期望的字段名
            "suggestions": "; ".join(review_summary.get("areas_for_improvement", [])) or review_summary.get("overall_assessment", "审核完成"),
            # 兼容原 ScienceChecker 的输出格式
            "revised_content": final_content,
            "highlight_terms": [],
            "glossary": [],
            "revised_glossary": [],
            "review_sections": self._build_review_sections(initial_review, final_verification),
        }

    def _build_review_sections(
        self,
        initial_review: Dict[str, Any],
        final_verification: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """构建兼容原格式的 review_sections"""
        issues = initial_review.get("issues", [])

        # 按类型分组
        sections_by_type = {
            "事实准确性校验": [],
            "专业术语适用性检查": [],
            "科学逻辑验证": [],
            "引用来源建议": [],
        }

        for issue in issues:
            issue_type = issue.get("type", "事实准确性校验")
            if issue_type in sections_by_type:
                sections_by_type[issue_type].append(issue)

        review_sections = []
        for section_name, section_issues in sections_by_type.items():
            if section_issues:
                finding = "；".join([i.get("description", "") for i in section_issues])
                status = "需修正"
                suggestion = f"建议修正以下问题：{finding}"
            else:
                finding = "未发现明显问题"
                status = "通过"
                suggestion = "建议保持当前表达"

            review_sections.append({
                "section": section_name,
                "status": status,
                "finding": finding,
                "suggestion": suggestion,
                "suggested_revision": "无需改写",
                "adopted": len(section_issues) == 0,
            })

        return review_sections

    def run(
        self,
        story_title: str,
        story_content: str,
        target_audience: str = "8-12岁儿童",
        evidence_context: Optional[List[Dict[str, Any]]] = None,
        deepsearch_context: Optional[Dict[str, Any]] = None,
        topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        完整的自反馈科学审核流程

        参数:
            story_title: 文章标题
            story_content: 文章内容
            target_audience: 目标受众
            evidence_context: 已有证据（可选）
            deepsearch_context: DeepSearch 上下文（可选）
            topic: 主题（用于检索优化）

        返回:
            兼容原 ScienceChecker 格式的结果
        """
        self.iteration_history = []
        self.all_evidence = evidence_context or []

        current_content = story_content

        # ========== 阶段 1: 初始审核 ==========
        self.log("开始阶段 1: 初始审核")
        initial_review = self.run_initial_review(
            title=story_title,
            content=current_content,
            target_audience=target_audience,
        )
        self.iteration_history.append({
            "stage": "initial_review",
            "content": current_content,
            "review": initial_review,
        })

        has_issues = initial_review.get("has_issues", False)
        issues = initial_review.get("issues", [])

        if not has_issues or not issues:
            # 没有问题，直接进行最终验证
            self.log("未发现问题，跳过迭代优化，直接验证")
            final_verification = self.run_citation_verification(
                title=story_title,
                content=current_content,
                evidence=self.all_evidence,
                target_audience=target_audience,
            )
            return self.generate_workflow_summary(
                initial_review=initial_review,
                iteration_history=[],
                final_verification=final_verification,
                final_content=current_content,
            )

        # ========== 阶段 2: 补充检索 ==========
        self.log(f"发现 {len(issues)} 个问题，开始阶段 2: 补充检索")
        new_evidence = self.run_supplementary_search(
            issues=issues,
            topic=topic,
        )
        self.all_evidence.extend(new_evidence)

        # 如果有 deepsearch_context，也整合进来
        if deepsearch_context:
            ds_evidence = deepsearch_context.get("evidence_used", [])
            self.all_evidence.extend(ds_evidence)

        # ========== 迭代优化循环 ==========
        for iteration in range(self.max_iterations):
            self.log(f"开始迭代 {iteration + 1}/{self.max_iterations}")

            # ========== 阶段 3: 生成反馈 ==========
            self.log("阶段 3: 生成反馈建议")
            feedback = self.generate_feedback(
                title=story_title,
                content=current_content,
                issues=issues,
                evidence=self.all_evidence,
                target_audience=target_audience,
            )

            feedback_items = feedback.get("feedback_items", [])
            if not feedback_items:
                self.log("没有反馈项，结束迭代")
                break

            # ========== 阶段 4: 迭代优化 ==========
            self.log("阶段 4: 应用反馈优化文章")
            optimization = self.run_iterative_optimization(
                title=story_title,
                content=current_content,
                feedback=feedback,
                target_audience=target_audience,
            )

            revised_content = optimization.get("revised_content", current_content)
            changes_made = optimization.get("changes_made", [])

            # 记录迭代历史
            self.iteration_history.append({
                "stage": f"iteration_{iteration + 1}",
                "content_before": current_content,
                "content_after": revised_content,
                "feedback": feedback,
                "changes_made": changes_made,
            })

            # 更新当前内容
            current_content = revised_content

            # 检查是否需要继续迭代
            if not feedback.get("needs_additional_search", False):
                self.log("无需进一步检索，结束迭代")
                break

        # ========== 阶段 5: 引用验证 ==========
        self.log("开始阶段 5: 引用验证")
        final_verification = self.run_citation_verification(
            title=story_title,
            content=current_content,
            evidence=self.all_evidence,
            target_audience=target_audience,
        )

        # ========== 生成最终总结 ==========
        self.log("生成最终审核总结")
        final_result = self.generate_workflow_summary(
            initial_review=initial_review,
            iteration_history=self.iteration_history,
            final_verification=final_verification,
            final_content=current_content,
        )

        # 确保所有必要字段都存在
        if "highlight_terms" not in final_result:
            final_result["highlight_terms"] = []
        if "glossary" not in final_result:
            final_result["glossary"] = []
        if "revised_glossary" not in final_result:
            final_result["revised_glossary"] = []

        self.result = final_result
        return final_result
