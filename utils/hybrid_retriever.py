"""
混合检索器 (Hybrid Retriever)
基于 OpenScholar 的多源检索整合机制
"""
import re
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


class RetrievalSource(Enum):
    """检索源枚举"""
    KIDSSCI_STORE = "kidssci_store"  # 儿童科普专用知识库
    WIKIPEDIA = "wikipedia"            # 维基百科（简单版）
    WEBSEARCH = "websearch"            # 网络搜索（限定学术/科普网站）
    DEEPSEARCH = "deepsearch"          # DeepSearch 服务


class HybridRetriever:
    """
    多源混合检索器

    检索优先级：
    1. KidsSci-Store（最权威、最适合儿童）
    2. Wikipedia Simple（简单易懂）
    3. WebSearch（限定权威科普网站）
    4. DeepSearch（兜底）
    """

    def __init__(self, db_session=None):
        self.db_session = db_session
        self.source_priority = [
            RetrievalSource.KIDSSCI_STORE,
            RetrievalSource.WIKIPEDIA,
            RetrievalSource.WEBSEARCH,
            RetrievalSource.DEEPSEARCH,
        ]

        # 时效性关键词 - 需要最新数据的主题
        self.timely_keywords = [
            "最新", "现在", "今天", "目前", "2024", "2025", "2026",
            "发现", "新研究", "科学家", "最近", "首次", "突破",
        ]

        # 权威网站白名单
        self.authoritative_sites = [
            "kepu.gov.cn",       # 科普中国
            "cdstm.cn",           # 中国数字科技馆
            "nasa.gov",           # NASA
            "esa.int",            # 欧空局
            "cas.cn",             # 中国科学院
            "nsfc.gov.cn",        # 国家自然科学基金
            "nature.com",         # Nature
            "science.org",        # Science
            "nationalgeographic.com",  # 国家地理
            "bbc.co.uk/news/science",  # BBC 科学
        ]

    def needs_timely_data(self, query: str) -> bool:
        """判断查询是否需要时效性数据"""
        return any(k in query for k in self.timely_keywords)

    def search(
        self,
        query: str,
        topic: Optional[str] = None,
        age_range: str = "8-12",
        max_results_per_source: int = 3,
        min_authority_level: int = 70,
    ) -> Dict[str, Any]:
        """
        多源混合检索

        参数:
            query: 检索查询
            topic: 主题（用于优化KidsSci-Store检索）
            age_range: 目标年龄段
            max_results_per_source: 每个源最多返回结果数
            min_authority_level: 最低权威度要求

        返回:
            {
                "results": [...],  // 合并后的结果
                "sources_used": [...],  // 使用的源
                "best_result": {...},  // 最佳结果
            }
        """
        all_results = []
        sources_used = []

        # 1. 优先检索 KidsSci-Store（如果有数据库会话）
        if self.db_session:
            try:
                kidssci_results = self._search_kidssci_store(
                    query, topic, age_range, max_results_per_source
                )
                if kidssci_results:
                    all_results.extend(kidssci_results)
                    sources_used.append(RetrievalSource.KIDSSCI_STORE.value)
            except Exception as e:
                print(f"[HybridRetriever] KidsSci-Store 检索失败: {e}")

        # 2. 如果结果不足，补充 Wikipedia
        if len(all_results) < max_results_per_source:
            try:
                wiki_results = self._search_wikipedia(
                    query, max_results_per_source
                )
                if wiki_results:
                    all_results.extend(wiki_results)
                    sources_used.append(RetrievalSource.WIKIPEDIA.value)
            except Exception as e:
                print(f"[HybridRetriever] Wikipedia 检索失败: {e}")

        # 3. 如果需要时效性数据，补充网络搜索
        if self.needs_timely_data(query) or len(all_results) < max_results_per_source:
            try:
                web_results = self._search_web(
                    query, max_results_per_source
                )
                if web_results:
                    all_results.extend(web_results)
                    sources_used.append(RetrievalSource.WEBSEARCH.value)
            except Exception as e:
                print(f"[HybridRetriever] WebSearch 检索失败: {e}")

        # 4. 结果合并、排序、去重
        merged_results = self._merge_and_rank_results(
            all_results, min_authority_level
        )

        # 找出最佳结果
        best_result = merged_results[0] if merged_results else None

        return {
            "results": merged_results,
            "sources_used": sources_used,
            "best_result": best_result,
            "query": query,
        }

    def _search_kidssci_store(
        self,
        query: str,
        topic: Optional[str],
        age_range: str,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """检索 KidsSci-Store（儿童科普专用知识库）"""
        from utils.fact_rag import search_fact_evidence

        try:
            results = search_fact_evidence(
                db=self.db_session,
                query=query,
                top_k=max_results,
                doc_type="SCIENCE_FACT",
            )

            # 统一格式
            formatted = []
            for r in results:
                formatted.append({
                    "source_name": r.get("source_name", "KidsSci-Store"),
                    "source_url": r.get("source_url"),
                    "authority_level": r.get("authority_level", 85),
                    "snippet": r.get("snippet", ""),
                    "retrieval_source": RetrievalSource.KIDSSCI_STORE.value,
                    "score": r.get("score", 0.8),
                })
            return formatted
        except Exception:
            return []

    def _search_wikipedia(
        self,
        query: str,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """检索维基百科（简单版优先）"""
        from utils.wikipedia_client import wikipedia_client

        try:
            results = wikipedia_client.search(
                query=query,
                simple=True,  # 优先简单英文维基或中文维基
                top_k=max_results,
            )

            formatted = []
            for r in results:
                formatted.append({
                    "source_name": "Wikipedia",
                    "source_url": r.get("url"),
                    "authority_level": 80,  # 维基百科权威度中等
                    "snippet": r.get("snippet", ""),
                    "retrieval_source": RetrievalSource.WIKIPEDIA.value,
                    "score": 0.7,
                })
            return formatted
        except Exception:
            return []

    def _search_web(
        self,
        query: str,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """网络搜索（限定权威网站）"""
        from utils.serpapi_client import serpapi_client

        try:
            # 构建站点限定查询
            site_query = self._build_site_restricted_query(query)

            results = serpapi_client.search(
                query=site_query,
                top_k=max_results,
            )

            formatted = []
            for r in results:
                # 评估来源权威度
                authority = self._estimate_authority_level(r.get("url", ""))
                formatted.append({
                    "source_name": r.get("source", "WebSearch"),
                    "source_url": r.get("url"),
                    "authority_level": authority,
                    "snippet": r.get("snippet", ""),
                    "retrieval_source": RetrievalSource.WEBSEARCH.value,
                    "score": 0.6,
                })
            return formatted
        except Exception:
            return []

    def _build_site_restricted_query(self, query: str) -> str:
        """构建站点限定的查询"""
        site_clauses = " OR ".join([f"site:{s}" for s in self.authoritative_sites[:5]])
        return f"({query}) AND ({site_clauses})"

    def _estimate_authority_level(self, url: str) -> int:
        """根据 URL 估算权威度"""
        if not url:
            return 60

        # 政府/学术机构网站
        if any(domain in url for domain in [".gov.cn", ".edu.cn", "cas.cn", "nsfc.gov.cn"]):
            return 90
        if any(domain in url for domain in [".gov", ".edu", ".ac.uk"]):
            return 85

        # 权威媒体/科普网站
        if any(domain in url for domain in ["kepu.gov.cn", "cdstm.cn", "nationalgeographic.com"]):
            return 88

        # 科学期刊
        if any(domain in url for domain in ["nature.com", "science.org"]):
            return 92

        # NASA/ESA 等航天机构
        if any(domain in url for domain in ["nasa.gov", "esa.int"]):
            return 90

        # 维基百科
        if "wikipedia.org" in url:
            return 80

        # 其他网站
        return 65

    def _merge_and_rank_results(
        self,
        results: List[Dict[str, Any]],
        min_authority_level: int,
    ) -> List[Dict[str, Any]]:
        """合并、排序、去重检索结果"""
        if not results:
            return []

        # 1. 过滤低权威度结果
        filtered = [
            r for r in results
            if r.get("authority_level", 0) >= min_authority_level
        ]

        if not filtered:
            filtered = results  # 如果都被过滤了，就用全部

        # 2. 计算综合得分
        for r in filtered:
            source_bonus = self._get_source_bonus(r.get("retrieval_source"))
            authority_bonus = (r.get("authority_level", 50) / 100.0)
            base_score = r.get("score", 0.5)
            r["combined_score"] = (
                0.4 * base_score +
                0.4 * source_bonus +
                0.2 * authority_bonus
            )

        # 3. 按综合得分排序
        sorted_results = sorted(
            filtered,
            key=lambda x: x.get("combined_score", 0),
            reverse=True
        )

        # 4. 去重（基于内容片段）
        seen_snippets = set()
        deduped = []
        for r in sorted_results:
            snippet = r.get("snippet", "")[:100]
            if snippet not in seen_snippets:
                seen_snippets.add(snippet)
                deduped.append(r)

        return deduped

    def _get_source_bonus(self, source: str) -> float:
        """获取源的优先级加分"""
        bonus_map = {
            RetrievalSource.KIDSSCI_STORE.value: 1.0,
            RetrievalSource.WIKIPEDIA.value: 0.8,
            RetrievalSource.WEBSEARCH.value: 0.6,
            RetrievalSource.DEEPSEARCH.value: 0.7,
        }
        return bonus_map.get(source, 0.5)
