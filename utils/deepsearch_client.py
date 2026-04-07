from typing import Any, Dict, List, Optional

from openai import OpenAI

from config.settings import settings
from utils.llm_client import llm_client


class DeepSearchClient:
    """轻量 DeepSearch 适配层：仅服务科学性审查步骤。"""

    def __init__(self):
        self.enabled = bool(settings.DEEPSEARCH_API_KEY and settings.DEEPSEARCH_MODEL)
        self.enable_search = bool(settings.DEEPSEARCH_ENABLE_SEARCH)
        self.client = None
        if self.enabled:
            self.client = OpenAI(
                api_key=settings.DEEPSEARCH_API_KEY,
                base_url=settings.DEEPSEARCH_API_BASE or settings.OPENAI_API_BASE,
            )

    def runtime_status(self) -> Dict[str, Any]:
        base = settings.DEEPSEARCH_API_BASE or settings.OPENAI_API_BASE
        key_tail = (settings.DEEPSEARCH_API_KEY or "")[-4:]
        return {
            "enabled": self.enabled,
            "model": settings.DEEPSEARCH_MODEL or "",
            "base": base,
            "enable_search": self.enable_search,
            "key_mask": f"***{key_tail}" if key_tail else "(empty)",
        }

    def _safe_int(self, value: Any, default: int = 70) -> int:
        try:
            return int(value)
        except Exception:
            return default

    def _pick_first(self, item: Dict[str, Any], keys: List[str], default: Optional[str] = None) -> Optional[str]:
        for key in keys:
            if key in item and str(item.get(key) or "").strip():
                return str(item.get(key)).strip()
        return default

    def _generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        if not self.enabled or not self.client:
            result = llm_client.generate_json(system_prompt, user_prompt)
            return result if isinstance(result, dict) else {}

        try:
            response = self.client.chat.completions.create(
                model=settings.DEEPSEARCH_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                extra_body={"enable_search": self.enable_search},
            )
            content = (response.choices[0].message.content or "").strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            import json

            parsed = json.loads(content.strip())
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            result = llm_client.generate_json(system_prompt, user_prompt)
            return result if isinstance(result, dict) else {}

    def search_science_context(
        self,
        title: str,
        content: str,
        target_audience: str = "大众",
        top_k: int = 6,
    ) -> Dict[str, Any]:
        safe_top_k = max(3, min(int(top_k or 6), 10))

        system_prompt = """你是 DeepSearch 证据检索助手，负责为科普科学审查提供结构化检索结果。
请严格返回 JSON，包含字段：
- evidence_used: 数组，元素结构 {evidence_id, source_name, source_url, authority_level, snippet}
- analysis_4d: 对象，必须包含四个键：事实准确性校验、专业术语适用性检查、科学逻辑验证、引用来源建议。
- glossary_candidates: 数组，元素结构 {term, explanation}，数量 6-12。
要求：
1) analysis_4d 的每个维度至少1条结论。
2) glossary_candidates 必须尽量来自正文语境。
3) evidence_used 至少返回 3 条，最多返回 top_k 条。
"""

        user_prompt = f"""请围绕以下文章执行深度检索并输出结构化结果：
【受众】{target_audience}
【标题】{title}
【正文】
{content}

请返回最多 {safe_top_k} 条 evidence_used。"""

        result = self._generate_json(system_prompt, user_prompt)
        if not isinstance(result, dict):
            result = {}

        evidence_used = result.get("evidence_used")
        analysis_4d = result.get("analysis_4d")
        glossary_candidates = result.get("glossary_candidates")

        if not isinstance(evidence_used, list):
            evidence_used = []
        if not isinstance(analysis_4d, dict):
            analysis_4d = {}
        if not isinstance(glossary_candidates, list):
            glossary_candidates = []

        # 兜底结构，避免上游解析不稳定。
        normalized_evidence: List[Dict[str, Any]] = []
        for idx, item in enumerate(evidence_used[:safe_top_k]):
            if not isinstance(item, dict):
                continue
            snippet = self._pick_first(item, ["snippet", "excerpt", "content"], "") or ""
            if not snippet:
                continue
            normalized_evidence.append(
                {
                    "evidence_id": self._pick_first(item, ["evidence_id", "id"], f"DS-{idx + 1}"),
                    "source_name": self._pick_first(item, ["source_name", "source", "publisher"], "DeepSearch"),
                    "source_url": self._pick_first(item, ["source_url", "url", "link"], None),
                    "authority_level": self._safe_int(item.get("authority_level"), 70),
                    "snippet": snippet,
                }
            )

        normalized_terms: List[Dict[str, str]] = []
        seen = set()
        for item in glossary_candidates[:12]:
            if not isinstance(item, dict):
                continue
            term = str(item.get("term") or "").strip()
            explanation = str(item.get("explanation") or "").strip()
            if not term:
                continue
            key = term.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized_terms.append(
                {
                    "term": term,
                    "explanation": explanation or f"{term}是文中核心科学概念，建议结合上下文理解。",
                }
            )

        return {
            "evidence_used": normalized_evidence,
            "analysis_4d": analysis_4d,
            "glossary_candidates": normalized_terms,
        }


deepsearch_client = DeepSearchClient()
