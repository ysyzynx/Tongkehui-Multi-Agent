from typing import Dict, Any, Optional, List, Tuple
import json
import re
import random
from sqlalchemy.orm import Session
from agent.base_agent import BaseAgent
from utils.llm_client import llm_client
from utils.fact_rag import search_fact_evidence, get_fact_evidence_by_ids
from utils.deepsearch_client import deepsearch_client
from prompts.story_creator_prompt import (
    STORY_SUGGEST_SYSTEM_PROMPT,
    STORY_SUGGEST_USER_PROMPT_TEMPLATE,
)
from prompts.story_creator_prompt_fun import (
    STORY_CREATOR_FUN_SYSTEM_PROMPT,
    STORY_CREATOR_FUN_USER_PROMPT_TEMPLATE,
)
from prompts.story_creator_prompt_encyclopedia import (
    STORY_CREATOR_ENC_SYSTEM_PROMPT,
    STORY_CREATOR_ENC_USER_PROMPT_TEMPLATE,
)

class StoryCreatorAgent(BaseAgent):
    """故事原创者Agent：接收用户参数，生成主题建议或完整的科普故事"""

    def __init__(self):
        super().__init__(name="Story Creator", description="Generates creative and scientific stories based on user parameters")

        self.system_prompt = STORY_CREATOR_FUN_SYSTEM_PROMPT

    def run(
        self,
        project_title: str = None,
        theme: str = None,
        age_group: str = None,
        style: str = None,
        target_audience: str = None,
        extra_requirements: str = None,
        word_count: int = 1200,
        db: Session = None,
        use_rag: bool = True,
        use_deepsearch: bool = False,
        deepsearch_top_k: int = 6,
        rag_doc_type: str = "SCIENCE_FACT",
        rag_top_k: int = 4,
        selected_rag_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        根据用户上传的关键词、年龄、文章风格，构建科普大纲和正文。
        利用封装的 llm_client 调用大模型生成格式化 JSON。
        支持 RAG 知识库检索增强创作。
        """

        # 处理可选参数的默认值
        final_theme = theme if theme else "令人惊奇的科学现象"
        final_project_title = (project_title or "").strip()
        final_age_group = age_group if age_group else "全年龄段"
        final_style = self._normalize_article_style(style)
        self.system_prompt, user_prompt_template = self._resolve_story_prompts(final_style)
        final_target = target_audience if target_audience else "普通大众（普及通用科学常识）"
        try:
            desired_word_count = int(word_count) if word_count is not None else 1200
        except (TypeError, ValueError):
            desired_word_count = 1200
        desired_word_count = max(300, min(5000, desired_word_count))

        # ========== RAG 知识库检索 ==========
        rag_evidence_block = ""
        rag_evidence_items = []
        if use_rag and db:
            # 构建检索查询：主题 + 标题
            search_query = f"{final_project_title or ''}\n{final_theme}".strip()

            # 如果用户指定了选中的文档ID，则只使用这些文档
            if selected_rag_ids and len(selected_rag_ids) > 0:
                try:
                    rag_evidence_items = get_fact_evidence_by_ids(
                        db,
                        doc_ids=selected_rag_ids,
                        top_k_per_doc=2
                    )
                except Exception:
                    # 检索失败时静默继续，不影响正常创作
                    rag_evidence_items = []
            # 否则正常检索相关文档
            elif search_query:
                try:
                    rag_evidence_items = search_fact_evidence(
                        db,
                        query=search_query,
                        top_k=rag_top_k or 4,
                        doc_type=rag_doc_type
                    )
                except Exception:
                    # 检索失败时静默继续，不影响正常创作
                    rag_evidence_items = []

            # 构建证据块提示词
            if rag_evidence_items:
                lines = []
                for idx, item in enumerate(rag_evidence_items, 1):
                    lines.append(
                        f"{idx}. [来源:{item.get('source_name', '未知')} | "
                        f"权威级:{item.get('authority_level', 0)}]\n"
                        f"   摘录: {item.get('snippet', '')}"
                    )
                rag_evidence_block = "\n【知识库参考材料】：\n" + "\n".join(lines)

        # ========== DeepSearch 可选增强 ==========
        deepsearch_evidence_items = []
        if use_deepsearch:
            try:
                ds_context = deepsearch_client.search_science_context(
                    title=final_project_title or final_theme,
                    content=final_theme,
                    target_audience=final_target,
                    top_k=deepsearch_top_k or 6,
                )
                deepsearch_evidence_items = ds_context.get("evidence_used", []) if isinstance(ds_context, dict) else []
            except Exception:
                deepsearch_evidence_items = []

        deepsearch_block = ""
        if deepsearch_evidence_items:
            lines = []
            for idx, item in enumerate(deepsearch_evidence_items[: max(3, min(int(deepsearch_top_k or 6), 10))], 1):
                if not isinstance(item, dict):
                    continue
                snippet = str(item.get("snippet") or "").strip()
                if not snippet:
                    continue
                lines.append(
                    f"{idx}. [来源:{item.get('source_name', 'DeepSearch')} | 权威级:{item.get('authority_level', 70)}]\n"
                    f"   摘录: {snippet}"
                )
            if lines:
                deepsearch_block = "\n【DeepSearch参考材料】：\n" + "\n".join(lines)

        evidence_block = f"{rag_evidence_block}{deepsearch_block}"

        # 处理自主设定的额外要求
        extra_prompt = ""
        if extra_requirements:
            extra_prompt = f"\n\n【用户给定的额外特殊设定要求】：\n{extra_requirements}\n（必须严格遵守并将以上特殊设定自然地融合进故事中！）"

        title_prompt = ""
        if final_project_title:
            title_prompt = (
                f"【项目标题要求】\n用户已确定项目标题为“{final_project_title}”。\n"
                "- 你输出的JSON中title字段必须与该标题高度相关，可在不偏题前提下做少量润色，但核心表达不能偏离。\n"
                "- 正文内容也必须紧密围绕该标题展开，避免出现标题与正文无关。"
            )

        user_prompt = user_prompt_template.format(
            final_theme=final_theme,
            final_target=final_target,
            final_age_group=final_age_group,
            final_style=final_style,
            desired_word_count=desired_word_count,
            title_prompt=title_prompt,
            extra_prompt=extra_prompt,
            rag_evidence_block=evidence_block,
        )

        # 调用大模型生成JSON结果
        initial_result = llm_client.generate_json(self.system_prompt, user_prompt)
        self.result = self._calibrate_story_length(
            initial_result=initial_result,
            desired_word_count=desired_word_count,
            max_retries=2,
        )
        self.result = self._normalize_story_punctuation(self.result)

        # 将使用的证据附加到结果中，方便追踪
        if rag_evidence_items:
            self.result["rag_evidence_used"] = rag_evidence_items
        self.result["rag_enabled"] = use_rag
        if deepsearch_evidence_items:
            self.result["deepsearch_evidence_used"] = deepsearch_evidence_items
        self.result["deepsearch_enabled"] = bool(use_deepsearch)

        return self.result

    def _normalize_article_style(self, style: Optional[str]) -> str:
        raw = str(style or "").strip()
        if not raw:
            return "趣味故事型"

        if "百科" in raw:
            return "百科全书型"

        if any(k in raw for k in ["趣味", "童话", "问答", "科普", "故事"]):
            return "趣味故事型"

        return raw

    def _resolve_story_prompts(self, style: str) -> Tuple[str, str]:
        if style == "百科全书型":
            return STORY_CREATOR_ENC_SYSTEM_PROMPT, STORY_CREATOR_ENC_USER_PROMPT_TEMPLATE
        return STORY_CREATOR_FUN_SYSTEM_PROMPT, STORY_CREATOR_FUN_USER_PROMPT_TEMPLATE

    def _content_length(self, text: str) -> int:
        # 中文“字数”场景下，按去除空白后的字符数统计更贴近用户感知。
        return len(re.sub(r"\s+", "", text or ""))

    def _is_length_acceptable(self, actual: int, desired: int) -> bool:
        # 比提示词中的±10%更严格，收紧到±5%。
        tolerance = max(20, int(desired * 0.05))
        return abs(actual - desired) <= tolerance

    def _build_rewrite_prompt(
        self,
        title: str,
        content: str,
        desired_word_count: int,
        actual_word_count: int,
    ) -> str:
        action = "扩写" if actual_word_count < desired_word_count else "精简"
        return (
            "请在保持科学准确性、章节结构与原有主题不偏离的前提下，对下列故事进行"
            f"{action}，使正文最终字数尽量贴近{desired_word_count}字。\n"
            "要求：\n"
            "1. 保留原有标题核心含义，不要跑题。\n"
            "2. 保持3-4章结构和叙事连贯性。\n"
            "3. 不要新增与主题无关的知识点。\n"
            "4. 标题与正文统一使用中文全角标点（，。；：！？（）\"\"《》），避免英文半角标点。\n"
            "5. 仅返回JSON，且只包含title与content字段。\n\n"
            f"当前字数（去空白统计）约为：{actual_word_count}。\n"
            f"目标字数：{desired_word_count}。\n\n"
            f"原始标题：{title}\n\n"
            "原始正文：\n"
            f"{content}"
        )

    def _calibrate_story_length(
        self,
        initial_result: Dict[str, Any],
        desired_word_count: int,
        max_retries: int = 2,
    ) -> Dict[str, Any]:
        # 异常结构直接返回，让上游统一错误处理兜底。
        if not isinstance(initial_result, dict):
            return initial_result

        best_result = initial_result
        best_content = str(best_result.get("content", "") or "")
        best_length = self._content_length(best_content)
        best_delta = abs(best_length - desired_word_count)

        if self._is_length_acceptable(best_length, desired_word_count):
            return best_result

        for _ in range(max_retries):
            current_title = str(best_result.get("title", "") or "")
            current_content = str(best_result.get("content", "") or "")
            current_length = self._content_length(current_content)

            rewrite_prompt = self._build_rewrite_prompt(
                title=current_title,
                content=current_content,
                desired_word_count=desired_word_count,
                actual_word_count=current_length,
            )
            retried = llm_client.generate_json(self.system_prompt, rewrite_prompt)

            if not isinstance(retried, dict):
                continue

            retried_content = str(retried.get("content", "") or "")
            retried_length = self._content_length(retried_content)
            retried_delta = abs(retried_length - desired_word_count)

            if retried_delta < best_delta:
                best_result = retried
                best_delta = retried_delta

            if self._is_length_acceptable(retried_length, desired_word_count):
                best_result = retried
                break

        return best_result

    def _normalize_story_punctuation(self, result: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return result

        normalized = dict(result)
        for key in ("title", "content"):
            if isinstance(normalized.get(key), str):
                normalized[key] = self._to_chinese_punctuation(normalized[key])
        return normalized

    def _to_chinese_punctuation(self, text: str) -> str:
        if not text:
            return text

        out = text

        # 1. 先处理成对的引号，将单引号和双引号都转换为中文双引号“”
        # 使用状态机处理引号配对，确保正确的左右引号
        def replace_quotes(content):
            in_quote = False
            output = []
            i = 0
            while i < len(content):
                char = content[i]
                if char in ('"', "'", "「", "」", "『", "』"):
                    if not in_quote:
                        # 左引号
                        output.append("“")
                        in_quote = True
                    else:
                        # 右引号
                        output.append("”")
                        in_quote = False
                else:
                    output.append(char)
                i += 1
            # 如果还有未闭合的引号，补充右引号
            if in_quote:
                output.append("”")
            return "".join(output)

        out = replace_quotes(out)

        # 2. 仅在中文上下文中替换半角标点，尽量避免影响英文缩写与数值格式。
        replacements = [
            (r"(?<=[\u4e00-\u9fff]),(?=[\u4e00-\u9fff0-9])", "，"),
            (r"(?<=[\u4e00-\u9fff0-9]),(?=[\u4e00-\u9fff])", "，"),
            (r"(?<=[\u4e00-\u9fff]);(?=[\u4e00-\u9fff0-9])", "；"),
            (r"(?<=[\u4e00-\u9fff]):(?=[\u4e00-\u9fff0-9])", "："),
            (r"(?<=[\u4e00-\u9fff])!(?=[\u4e00-\u9fff0-9]|\s|$)", "！"),
            (r"(?<=[\u4e00-\u9fff])\?(?=[\u4e00-\u9fff0-9]|\s|$)", "？"),
            (r"(?<=[\u4e00-\u9fff])\((?=[^)]*[\u4e00-\u9fff])", "（"),
            (r"(?<=[\u4e00-\u9fff\u3002\uff01\uff1f\uff1b\uff1a])\)", "）"),
            # 处理句号：避免替换小数点
            (r"(?<=[\u4e00-\u9fff])\.(?=[\u4e00-\u9fff]|\s|$)", "。"),
        ]

        for pattern, replacement in replacements:
            out = re.sub(pattern, replacement, out)

        return out

    def suggest_titles(
        self,
        theme: str,
        target_audience: str = None,
        age_group: str = None,
    ) -> Dict[str, Any]:
        """基于用户输入主题，生成4条标题建议（含主题归类与说明）。"""
        final_theme = (theme or "令人惊奇的科学现象").strip()
        final_target = target_audience or "青少幼年儿童"
        final_age_group = age_group or "6-12岁"

        suggest_system_prompt = STORY_SUGGEST_SYSTEM_PROMPT

        suggest_user_prompt = STORY_SUGGEST_USER_PROMPT_TEMPLATE.format(
            final_theme=final_theme,
            final_target=final_target,
            final_age_group=final_age_group,
        )

        result = llm_client.generate_json(suggest_system_prompt, suggest_user_prompt)
        if isinstance(result, dict) and isinstance(result.get("suggestions"), list):
            normalized = self._normalize_suggestions(result.get("suggestions", []))
            diversified = self._select_diverse_suggestions(normalized, desired=4)
            if len(diversified) == 4:
                return {"suggestions": diversified}

        # LLM异常时回退到高差异模板，避免反复出现同构标题。
        fallback = self._fallback_suggestions(final_theme)
        return {"suggestions": self._select_diverse_suggestions(fallback, desired=4)}

    def _normalize_suggestions(self, suggestions: List[Any]) -> List[Dict[str, str]]:
        normalized: List[Dict[str, str]] = []
        for item in suggestions:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            category = str(item.get("category", "")).strip()
            clue = str(item.get("clue", "")).strip()
            if title and category and clue:
                normalized.append({"title": title, "category": category, "clue": clue})
        return normalized

    def _title_key(self, title: str) -> str:
        # 归一化标题，去除标点与空白后用于去重。
        compact = re.sub(r"[^\w\u4e00-\u9fff]", "", title or "").lower()
        return compact

    def _leading_pattern(self, title: str) -> str:
        # 取标题前缀模式，降低“同句式扎堆”的概率。
        text = (title or "").strip()
        if not text:
            return ""
        for sep in ["：", ":", "？", "!", "！", "-", "——"]:
            if sep in text:
                return text.split(sep, 1)[0].strip().lower()
        return text[:8].lower()

    def _select_diverse_suggestions(self, suggestions: List[Dict[str, str]], desired: int = 4) -> List[Dict[str, str]]:
        if not suggestions:
            return []

        # 1) 强去重：标题去重
        seen_title = set()
        deduped: List[Dict[str, str]] = []
        for item in suggestions:
            key = self._title_key(item.get("title", ""))
            if not key or key in seen_title:
                continue
            seen_title.add(key)
            deduped.append(item)

        # 2) 按类别和句式分散抽取
        picked: List[Dict[str, str]] = []
        used_category = set()
        used_pattern = set()

        # 首轮：优先类别分散 + 句式分散
        for item in deduped:
            if len(picked) >= desired:
                break
            category = item.get("category", "")
            pattern = self._leading_pattern(item.get("title", ""))
            if category in used_category or pattern in used_pattern:
                continue
            picked.append(item)
            used_category.add(category)
            used_pattern.add(pattern)

        # 次轮：补齐类别分散
        if len(picked) < desired:
            for item in deduped:
                if len(picked) >= desired:
                    break
                if item in picked:
                    continue
                category = item.get("category", "")
                if category in used_category:
                    continue
                picked.append(item)
                used_category.add(category)

        # 末轮：仍不足则按去重后顺序补齐
        if len(picked) < desired:
            for item in deduped:
                if len(picked) >= desired:
                    break
                if item in picked:
                    continue
                picked.append(item)

        return picked[:desired]

    def _fallback_suggestions(self, theme: str) -> List[Dict[str, str]]:
        # 提供更大的回退候选池，降低重复结构概率。
        pool: List[Tuple[str, str, str]] = [
            (f"{theme}奇遇记：一场会说话的科学线索", "科普活动", "用连续情节带出核心概念"),
            (f"{theme}为什么会发生？从一个问题开始追踪", "科普活动", "以提问驱动逐步解释原理"),
            (f"{theme}观察笔记：把日常现象变成小发现", "科普活动", "强调观察方法与证据意识"),
            (f"{theme}动手试一试：5分钟家庭小实验", "科普活动", "突出可操作性与复现实验"),
            (f"{theme}与健康的关系：身体里的科学提示", "健康与医疗", "连接生活习惯和科学机制"),
            (f"{theme}安全通关手册：遇到情况先这样做", "应急避险", "结合场景给出实用判断路径"),
            (f"{theme}餐桌上的真相：怎么吃更安心", "食品安全", "把知识点落到日常饮食选择"),
            (f"{theme}能源侦探队：看不见的能量在流动", "能源利用", "讲清能量来源与使用效率"),
            (f"{theme}太空视角：如果把问题搬到宇宙里", "航空航天", "通过对比扩展科学想象边界"),
            (f"{theme}谣言粉碎机：一眼识别伪科学套路", "伪科学", "训练证据判断与逻辑思维"),
            (f"{theme}与环境的连锁反应：一件小事的蝴蝶效应", "气候与环境前沿技术", "突出系统性因果关系"),
            (f"{theme}任务挑战书：今天你来做小研究员", "科普活动", "用任务机制增强参与感"),
        ]
        random.shuffle(pool)
        return [{"title": t, "category": c, "clue": clue} for t, c, clue in pool]

