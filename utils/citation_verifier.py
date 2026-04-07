"""
引用验证器 (Citation Verifier)
基于 OpenScholar 的引用验证机制
"""
import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class StatementType(Enum):
    """科学论断类型"""
    FACT = "fact"                    # 事实陈述
    NUMERIC = "numeric"              # 数值数据
    DEFINITION = "definition"        # 概念定义
    MECHANISM = "mechanism"          # 科学原理
    HISTORICAL = "historical"        # 历史事件


class VerificationStatus(Enum):
    """验证状态"""
    FULLY_SUPPORTED = "fully_supported"    # 完全有支撑
    PARTIALLY_SUPPORTED = "partially_supported"  # 部分有支撑
    NOT_SUPPORTED = "not_supported"        # 无支撑
    UNCERTAIN = "uncertain"                # 不确定


@dataclass
class ScienceStatement:
    """科学论断"""
    statement_id: str
    text: str
    statement_type: StatementType
    location: str  # 在文中的位置描述
    verification_status: VerificationStatus
    supporting_evidence: List[Dict[str, Any]]
    confidence: float
    citation_mark: Optional[str] = None


@dataclass
class Citation:
    """引用"""
    citation_id: str
    mark: str  # [1], [2], ...
    source_name: str
    source_url: Optional[str]
    snippet: str
    authority_level: int
    statements_supported: List[str]  # 这个引用支撑的论断 ID 列表


class CitationVerifier:
    """
    引用验证器

    功能：
    1. 从文章中提取科学论断
    2. 验证每个论断是否有证据支撑
    3. 为有支撑的论断添加引用标记
    4. 生成引用列表
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.statements: List[ScienceStatement] = []
        self.citations: List[Citation] = []

    def verify_content(
        self,
        content: str,
        evidence: List[Dict[str, Any]],
        title: str = "",
        target_audience: str = "8-12岁儿童",
    ) -> Dict[str, Any]:
        """
        验证文章中的科学论断

        参数:
            content: 文章内容
            evidence: 检索到的证据列表
            title: 文章标题
            target_audience: 目标受众

        返回:
            {
                "all_supported": true/false,
                "statements": [...],
                "citations": [...],
                "content_with_citations": "...",
                "final_pass": true/false,
                "review_summary": {...}
            }
        """
        # 1. 提取科学论断
        self.statements = self._extract_science_statements(
            content, title, target_audience
        )

        if not self.statements:
            return {
                "all_supported": True,
                "statements": [],
                "citations": [],
                "content_with_citations": content,
                "final_pass": True,
                "review_summary": self._build_review_summary([])
            }

        # 2. 验证每个论断
        for stmt in self.statements:
            supporting = self._find_supporting_evidence(stmt, evidence)
            stmt.supporting_evidence = supporting

            if supporting:
                stmt.verification_status = VerificationStatus.FULLY_SUPPORTED
                stmt.confidence = self._calculate_confidence(stmt, supporting)
            else:
                stmt.verification_status = VerificationStatus.NOT_SUPPORTED
                stmt.confidence = 0.0

        # 3. 分配引用标记
        self.citations = self._assign_citations(self.statements, evidence)

        # 4. 生成带引用标记的文章
        content_with_citations = self._insert_citation_marks(
            content, self.statements, self.citations
        )

        # 5. 构建最终结果
        all_supported = all(
            s.verification_status == VerificationStatus.FULLY_SUPPORTED
            for s in self.statements
        )

        final_pass = all_supported or len([
            s for s in self.statements
            if s.verification_status == VerificationStatus.NOT_SUPPORTED
        ]) <= 1  # 允许 1 个无支撑的论断

        return {
            "all_supported": all_supported,
            "statements": [self._statement_to_dict(s) for s in self.statements],
            "citations": [self._citation_to_dict(c) for c in self.citations],
            "content_with_citations": content_with_citations,
            "final_pass": final_pass,
            "review_summary": self._build_review_summary(self.statements)
        }

    def _extract_science_statements(
        self,
        content: str,
        title: str,
        target_audience: str,
    ) -> List[ScienceStatement]:
        """
        从文章中提取科学论断

        什么需要验证：
        - 陈述事实的句子
        - 包含数值、数据的句子
        - 定义科学概念的句子
        - 描述科学原理的句子

        什么不需要验证：
        - 主观描述（"这真是太神奇了！"）
        - 故事性内容（"小明决定去探索"）
        - 比喻、拟人等修辞手法
        """
        # 这里使用简单规则提取，实际使用时可以用 LLM
        statements = []
        import re

        # 按句子分割
        sentences = re.split(r'[。！？!?]', content)
        sentence_id = 0

        for idx, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue

            # 检查是否是科学论断（简单规则）
            if self._is_science_statement(sentence):
                stmt_type = self._classify_statement(sentence)
                statements.append(ScienceStatement(
                    statement_id=f"STMT-{sentence_id + 1}",
                    text=sentence + "。",
                    statement_type=stmt_type,
                    location=f"第 {idx + 1} 句附近",
                    verification_status=VerificationStatus.UNCERTAIN,
                    supporting_evidence=[],
                    confidence=0.5,
                ))
                sentence_id += 1

        return statements

    def _is_science_statement(self, sentence: str) -> bool:
        """判断是否是科学论断（简单规则）"""
        # 科学关键词
        science_keywords = [
            "是", "有", "在", "可以", "能", "会",
            "温度", "速度", "距离", "时间", "年龄", "大小",
            "因为", "所以", "导致", "造成", "通过",
            "恐龙", "太阳", "地球", "植物", "动物", "细胞", "基因",
            "米", "公里", "千克", "度", "年", "万", "亿",
        ]

        # 排除主观描述
        subjective_keywords = [
            "我觉得", "我认为", "真是", "太神奇", "太有趣",
            "小朋友", "我们", "你", "大家",
            "决定", "想要", "喜欢", "开心", "惊讶",
        ]

        if any(k in sentence for k in subjective_keywords):
            return False

        # 太短的句子可能不是
        if len(sentence) < 5:
            return False

        # 包含数字的句子很可能是
        if any(char.isdigit() for char in sentence):
            return True

        # 包含科学关键词
        if any(k in sentence for k in science_keywords[:30]):
            return True

        return False

    def _classify_statement(self, sentence: str) -> StatementType:
        """分类科学论断类型"""
        if any(char.isdigit() for char in sentence):
            return StatementType.NUMERIC

        if "是" in sentence and len(sentence) < 30:
            return StatementType.DEFINITION

        if "因为" in sentence or "所以" in sentence or "通过" in sentence:
            return StatementType.MECHANISM

        if "年" in sentence and "前" in sentence:
            return StatementType.HISTORICAL

        return StatementType.FACT

    def _find_supporting_evidence(
        self,
        statement: ScienceStatement,
        evidence: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """找到支撑这个论断的证据"""
        supporting = []

        stmt_text = statement.text.lower()

        for ev in evidence:
            snippet = str(ev.get("snippet", "")).lower()

            # 简单匹配：检查关键词重叠
            stmt_words = set(stmt_text.replace("，", "").replace("。", "").split())
            snippet_words = set(snippet.split())

            if not stmt_words or not snippet_words:
                continue

            overlap = len(stmt_words.intersection(snippet_words))
            overlap_ratio = overlap / max(1, len(stmt_words))

            if overlap_ratio >= 0.3:  # 至少 30% 的关键词重叠
                supporting.append({
                    **ev,
                    "relevance_score": overlap_ratio,
                })

        # 按相关性排序
        supporting.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return supporting[:3]  # 最多 3 个支撑证据

    def _calculate_confidence(
        self,
        statement: ScienceStatement,
        evidence: List[Dict[str, Any]],
    ) -> float:
        """计算置信度"""
        if not evidence:
            return 0.0

        # 基于证据权威度和相关性
        total = 0.0
        for ev in evidence:
            authority = ev.get("authority_level", 50) / 100.0
            relevance = ev.get("relevance_score", 0.5)
            total += 0.6 * authority + 0.4 * relevance

        return min(1.0, total / max(1, len(evidence)))

    def _assign_citations(
        self,
        statements: List[ScienceStatement],
        evidence: List[Dict[str, Any]],
    ) -> List[Citation]:
        """为证据分配引用标记"""
        citations = []
        citation_num = 1

        # 为每个证据创建引用
        seen_sources = {}  # 去重相同来源

        for stmt in statements:
            for ev in stmt.supporting_evidence:
                source_key = f"{ev.get('source_name')}:{ev.get('snippet', '')[:50]}"

                if source_key not in seen_sources:
                    citation = Citation(
                        citation_id=f"CIT-{citation_num}",
                        mark=f"[{citation_num}]",
                        source_name=ev.get("source_name", "未知来源"),
                        source_url=ev.get("source_url"),
                        snippet=ev.get("snippet", ""),
                        authority_level=ev.get("authority_level", 70),
                        statements_supported=[stmt.statement_id],
                    )
                    citations.append(citation)
                    seen_sources[source_key] = citation
                    citation_num += 1
                else:
                    # 已有引用，添加支撑的论断
                    citation = seen_sources[source_key]
                    if stmt.statement_id not in citation.statements_supported:
                        citation.statements_supported.append(stmt.statement_id)

                # 为论断设置引用标记
                stmt.citation_mark = seen_sources[source_key].mark

        return citations

    def _insert_citation_marks(
        self,
        content: str,
        statements: List[ScienceStatement],
        citations: List[Citation],
    ) -> str:
        """在文章中插入引用标记"""
        # 这里简化处理：在每个论断后添加第一个引用标记
        result = content

        for stmt in statements:
            if stmt.citation_mark and stmt.text in result:
                # 在论断后添加引用标记
                old_text = stmt.text
                if old_text.endswith("。"):
                    new_text = old_text[:-1] + stmt.citation_mark + "。"
                else:
                    new_text = old_text + stmt.citation_mark
                result = result.replace(old_text, new_text)

        return result

    def _statement_to_dict(self, stmt: ScienceStatement) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "statement_id": stmt.statement_id,
            "text": stmt.text,
            "type": stmt.statement_type.value,
            "location": stmt.location,
            "supported": stmt.verification_status == VerificationStatus.FULLY_SUPPORTED,
            "status": stmt.verification_status.value,
            "supporting_evidence": stmt.supporting_evidence,
            "confidence": stmt.confidence,
            "citation_mark": stmt.citation_mark,
        }

    def _citation_to_dict(self, citation: Citation) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "citation_id": citation.citation_id,
            "mark": citation.mark,
            "source_name": citation.source_name,
            "source_url": citation.source_url,
            "snippet": citation.snippet,
            "authority_level": citation.authority_level,
            "statements_supported": citation.statements_supported,
        }

    def _build_review_summary(
        self,
        statements: List[ScienceStatement],
    ) -> Dict[str, Any]:
        """构建审核总结"""
        if not statements:
            return {
                "overall_assessment": "未检测到需要验证的科学论断",
                "strengths": ["内容适合目标受众"],
                "areas_for_improvement": [],
                "recommendation": "建议通过",
            }

        total = len(statements)
        fully_supported = len([
            s for s in statements
            if s.verification_status == VerificationStatus.FULLY_SUPPORTED
        ])
        partially_supported = len([
            s for s in statements
            if s.verification_status == VerificationStatus.PARTIALLY_SUPPORTED
        ])
        not_supported = len([
            s for s in statements
            if s.verification_status == VerificationStatus.NOT_SUPPORTED
        ])

        strengths = []
        areas = []

        if fully_supported == total:
            strengths.append("所有科学论断都有权威证据支撑")
            strengths.append("科学准确性高")
            recommendation = "建议通过"
        elif not_supported <= 1:
            strengths.append("大部分科学论断有证据支撑")
            areas.append(f"有 {not_supported} 个论断需要补充证据")
            recommendation = "建议修改后通过"
        else:
            areas.append(f"有 {not_supported} 个论断缺乏证据支撑")
            recommendation = "建议补充证据后再通过"

        avg_confidence = sum(s.confidence for s in statements) / total
        if avg_confidence >= 0.8:
            strengths.append("证据置信度高")
        elif avg_confidence >= 0.6:
            pass
        else:
            areas.append("建议补充更权威的证据来源")

        return {
            "overall_assessment": f"共验证 {total} 个科学论断，{fully_supported} 个完全有支撑",
            "strengths": strengths,
            "areas_for_improvement": areas,
            "recommendation": recommendation,
            "stats": {
                "total_statements": total,
                "fully_supported": fully_supported,
                "partially_supported": partially_supported,
                "not_supported": not_supported,
                "average_confidence": round(avg_confidence, 2),
            }
        }
