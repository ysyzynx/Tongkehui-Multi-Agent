import json
import re
from typing import Dict, Any, List, Optional
from agent.base_agent import BaseAgent
from utils.llm_client import llm_client
from prompts.science_checker_prompt import (
    SCIENCE_CHECKER_SYSTEM_PROMPT,
    SCIENCE_CHECKER_USER_PROMPT_TEMPLATE,
)


SECTION_ORDER = [
    "事实准确性校验",
    "专业术语适用性检查",
    "科学逻辑验证",
    "引用来源建议",
]

SECTION_KEYWORDS = {
    "事实准确性校验": ["事实", "错误", "不准确", "数值", "概念", "偏差", "误导", "不当", "不严谨", "定义"],
    "专业术语适用性检查": ["术语", "词", "表达", "比喻", "解释", "理解", "难懂", "小朋友", "受众", "通俗"],
    "科学逻辑验证": ["逻辑", "因果", "推理", "机制", "关系", "过程", "链条", "前后", "矛盾", "论证"],
    "引用来源建议": ["来源", "引用", "文献", "资料", "数据库", "NASA", "权威", "出处", "机构", "教材"],
}

SCIENCE_TERM_HINTS = [
    # 天文学
    "太阳", "恒星", "行星", "卫星", "彗星", "黑洞", "白矮星", "红巨星", "中子星",
    "银河", "宇宙", "星系", "星云", "星团", "超新星", "日食", "月食", "潮汐",
    "太阳系", "银河系", "小行星", "流星", "陨石", "天文台", "望远镜",
    # 物理学
    "引力", "重力", "万有引力", "速度", "加速度", "动能", "势能", "能量", "功",
    "光", "光子", "光线", "光源", "光速", "反射", "折射", "散射", "色散",
    "电磁波", "波长", "频率", "辐射", "红外线", "紫外线", "可见光", "X射线",
    "温度", "压强", "密度", "体积", "质量", "重量", "力", "牛顿", "焦耳",
    "电", "电流", "电压", "电阻", "电路", "磁铁", "磁场", "电磁感应",
    "原子", "分子", "离子", "电子", "质子", "中子", "原子核", "粒子",
    "核聚变", "核裂变", "核反应", "放射性", "同位素", "量子", "相对论",
    "声", "声音", "声波", "频率", "振幅", "超声波", "次声波",
    "热", "热量", "传导", "对流", "辐射", "熔点", "沸点", "凝固", "蒸发",
    # 化学
    "元素", "化合物", "混合物", "原子", "分子", "离子", "化学键",
    "酸", "碱", "盐", "pH值", "氧化", "还原", "催化剂", "反应",
    "金属", "非金属", "有机物", "无机物", "晶体", "溶液", "溶解", "沉淀",
    "碳", "氢", "氧", "氮", "钙", "铁", "锌", "钾", "钠", "镁",
    # 生物学
    "细胞", "细胞膜", "细胞核", "细胞质", "细胞壁", "叶绿体", "线粒体",
    "DNA", "RNA", "基因", "染色体", "遗传", "变异", "进化", "进化论",
    "微生物", "细菌", "病毒", "真菌", "原生生物", "细胞分裂", "有丝分裂",
    "新陈代谢", "光合作用", "呼吸作用", "消化", "循环", "神经", "激素",
    "生态", "生态系统", "种群", "群落", "食物链", "食物网", "生产者",
    "消费者", "分解者", "生物圈", "栖息地", "生物多样性", "物种", "灭绝",
    "根", "茎", "叶", "花", "果实", "种子", "授粉", "发芽", "光合作用",
    "心脏", "肺", "胃", "肠", "肝", "肾", "脑", "神经", "肌肉", "骨骼",
    # 地球科学
    "大气", "大气层", "气候", "天气", "温度", "湿度", "气压", "风",
    "云", "雨", "雪", "冰雹", "霜", "露", "雾", "台风", "飓风",
    "地壳", "地幔", "地核", "板块", "地震", "火山", "岩浆", "岩石",
    "矿物", "化石", "土壤", "侵蚀", "沉积", "变质", "山脉", "峡谷",
    "海洋", "河流", "湖泊", "冰川", "地下水", "水循环", "碳循环",
    # 环境科学
    "污染", "环保", "生态", "温室效应", "全球变暖", "臭氧层", "酸雨",
    "可持续发展", "资源", "能源", "再生能源", "太阳能", "风能", "水能",
    # 科学方法
    "观察", "假设", "实验", "验证", "结论", "理论", "定律", "公理",
    "测量", "计算", "数据", "分析", "归纳", "演绎", "推理",
]

NON_SCIENCE_TERM_HINTS = [
    "守护者", "勇士", "精灵", "魔法", "英雄", "小朋友", "小明", "小雨", "雷克斯",
    "猫头鹰", "老师", "博士", "爷爷", "奶奶", "妈妈", "爸爸", "同学", "朋友",
    "冒险", "奇遇", "故事", "情节", "对话", "台词",
]

COMMON_NON_TERM_WORDS = {
    "我们", "你们", "他们", "自己", "这个", "那个", "这些", "那些", "一种", "一个", "一些",
    "因为", "所以", "如果", "但是", "然后", "于是", "已经", "可以", "需要", "通过", "进行",
    "并且", "以及", "或者", "其中", "为了", "这里", "那里", "大家", "孩子", "老师", "故事",
}

GENERIC_EXPLANATION_FLAGS = [
    "建议结合上下文理解",
    "关键概念",
    "进一步理解",
    "文中涉及的科学词汇",
]

SCIENCE_EXPLANATION_PRESETS = [
    {"keywords": ["表面张力"], "explanation": "表面张力是液体表面分子受力不均产生的收缩效应，使液面趋向于最小面积。"},
    {"keywords": ["水膜"], "explanation": "水膜是液体在界面上形成的薄层结构，能在一定条件下包裹气体或附着在固体表面。"},
    {"keywords": ["水分子", "分子"], "explanation": "分子是由原子组成并保持物质化学性质的最小微粒；水分子由两个氢原子和一个氧原子构成。"},
    {"keywords": ["重力", "万有引力", "引力"], "explanation": "重力是地球对物体产生的吸引作用，本质上属于万有引力在地表附近的表现。"},
    {"keywords": ["浮力"], "explanation": "浮力是流体对浸入物体产生的向上托举力，其大小与排开流体的重量有关。"},
    {"keywords": ["密度"], "explanation": "密度表示单位体积物质的质量，常用于比较不同物质“轻重”差异。"},
    {"keywords": ["压强"], "explanation": "压强是单位面积上受到的压力大小，常用于描述流体和固体受力情况。"},
    {"keywords": ["蒸发"], "explanation": "蒸发是液体表面分子获得足够能量后逃逸到气相的过程。"},
    {"keywords": ["凝结", "冷凝"], "explanation": "凝结是气体分子失去能量后转变为液体的过程。"},
    {"keywords": ["折射"], "explanation": "折射是光从一种介质进入另一种介质时传播方向发生改变的现象。"},
    {"keywords": ["反射"], "explanation": "反射是光遇到界面后返回原介质传播的现象。"},
    {"keywords": ["呼吸作用"], "explanation": "呼吸作用是生物细胞分解有机物并释放能量的过程，通常伴随氧气消耗和二氧化碳产生。"},
    {"keywords": ["微生物"], "explanation": "微生物是个体微小、通常需借助显微镜观察的生物类群，包括细菌、真菌和部分原生生物等。"},
    {"keywords": ["碳循环"], "explanation": "碳循环是碳元素在大气、水体、土壤和生物体之间不断迁移与转化的过程。"},
    {"keywords": ["固碳量", "固碳"], "explanation": "固碳量指生态系统通过光合作用等过程将二氧化碳转化并储存在有机物中的总量。"},
    {"keywords": ["卫星"], "explanation": "卫星是围绕行星等天体运行的天体，既包括天然卫星，也包括人造卫星。"},
    {"keywords": ["声音", "声波"], "explanation": "声音是由物体振动产生并通过介质传播的机械波，其传播速度与介质性质有关。"},
    {"keywords": ["氧化"], "explanation": "氧化是物质失去电子或与氧发生反应的化学过程，常与还原反应成对出现。"},
]

class ScienceCheckerAgent(BaseAgent):
    """科学审核者Agent：校验科普事实，排查科学逻辑错误和AI幻觉，返回审查结果和修正建议"""

    def __init__(self):
        super().__init__(name="Science Checker", description="Verifies scientific facts in generated story and suggests corrections.")
        self.system_prompt = SCIENCE_CHECKER_SYSTEM_PROMPT

    def _to_string_list(self, value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _normalize_evidence_used(self, value: Any) -> List[Dict[str, Any]]:
        if not isinstance(value, list):
            return []

        normalized: List[Dict[str, Any]] = []
        for idx, item in enumerate(value):
            if not isinstance(item, dict):
                continue
            snippet = str(item.get("snippet") or item.get("excerpt") or item.get("content") or "").strip()
            source_name = str(item.get("source_name") or item.get("source") or "DeepSearch").strip() or "DeepSearch"
            source_url = str(item.get("source_url") or item.get("url") or item.get("link") or "").strip() or None
            evidence_id = str(item.get("evidence_id") or item.get("id") or f"E-{idx + 1}").strip() or f"E-{idx + 1}"
            try:
                authority_level = int(item.get("authority_level") or 70)
            except Exception:
                authority_level = 70

            if not snippet:
                continue

            normalized.append(
                {
                    "evidence_id": evidence_id,
                    "source_name": source_name,
                    "source_url": source_url,
                    "authority_level": authority_level,
                    "snippet": snippet,
                }
            )

        return normalized

    def _extract_context_sentence(self, content: str, term: str) -> str:
        text = str(content or "").replace("\n", " ").strip()
        if not text or not term:
            return ""
        index = text.find(term)
        if index < 0:
            return ""

        left = max(
            text.rfind("。", 0, index),
            text.rfind("！", 0, index),
            text.rfind("？", 0, index),
        )
        right_candidates = [
            p for p in [
                text.find("。", index),
                text.find("！", index),
                text.find("？", index),
            ] if p >= 0
        ]
        right = min(right_candidates) if right_candidates else min(len(text), index + len(term) + 32)
        start = 0 if left < 0 else left + 1
        return text[start:right + 1].strip()

    def _build_scientific_explanation(self, term: str, content: str, existing: str = "") -> str:
        term_text = str(term or "").strip()
        existing_text = str(existing or "").strip()

        if existing_text and not any(flag in existing_text for flag in GENERIC_EXPLANATION_FLAGS):
            return existing_text

        for preset in SCIENCE_EXPLANATION_PRESETS:
            if any(keyword in term_text for keyword in preset["keywords"]):
                return preset["explanation"]

        context = self._extract_context_sentence(content, term_text)
        if context:
            return (
                f"{term_text}是本文中的科学术语，用于解释相关现象或机制。"
                "建议从“定义是什么、在什么条件下成立、会带来什么结果”三个维度理解该词条。"
            )

        return (
            f"{term_text}是本文中的科学术语。"
            "建议从“定义、机制、适用条件、典型现象”四个维度理解该概念。"
        )

    def _generate_scientific_explanations_by_llm(
        self,
        terms: List[str],
        story_title: str,
        story_content: str,
        target_audience: str,
    ) -> Dict[str, str]:
        normalized_terms = [str(term or "").strip() for term in terms if str(term or "").strip()]
        if not normalized_terms:
            return {}

        # 控制上下文长度，降低成本并提升稳定性。
        content_excerpt = str(story_content or "")[:2000]

        system_prompt = (
            "你是一名百科词条编写专家。"
            "请仅针对给定术语生成科学、客观、可核验的解释。"
            "解释要避免文学化和情绪化，不要复述剧情，不要输出无关内容。"
            "必须返回JSON。"
        )

        user_prompt = (
            "请为下列术语生成文末词条解释，要求：\n"
            "1) 每个术语必须给出1-2句科学解释；\n"
            "2) 优先采用百科词条风格，先定义，再补充机制/作用/边界；\n"
            "3) 解释必须与本文语境相关，但不能照抄原文句子；\n"
            "4) 不确定时给出保守且正确的通用科学定义；\n"
            "5) 仅返回JSON，格式：{\"glossary\":[{\"term\":\"术语\",\"explanation\":\"解释\"}]}。\n\n"
            f"目标受众：{target_audience or '大众'}\n"
            f"文章标题：{story_title or '未命名故事'}\n"
            f"术语列表：{json.dumps(normalized_terms, ensure_ascii=False)}\n"
            f"正文摘要：\n{content_excerpt}"
        )

        try:
            result = llm_client.generate_json(system_prompt, user_prompt)
        except Exception:
            return {}

        if not isinstance(result, dict):
            return {}

        glossary = result.get("glossary")
        if not isinstance(glossary, list):
            return {}

        allowed = {term.lower(): term for term in normalized_terms}
        explanation_map: Dict[str, str] = {}

        for item in glossary:
            if not isinstance(item, dict):
                continue
            term = str(item.get("term") or "").strip()
            explanation = str(item.get("explanation") or "").strip()
            if not term or not explanation:
                continue
            key = term.lower()
            if key not in allowed:
                continue
            explanation_map[allowed[key]] = explanation

        return explanation_map

    def _align_glossary_with_highlight_terms(
        self,
        highlight_terms: List[str],
        glossary_items: List[Dict[str, str]],
        story_title: str,
        story_content: str,
        target_audience: str,
    ) -> List[Dict[str, str]]:
        terms = [str(t or "").strip() for t in (highlight_terms or []) if str(t or "").strip()]
        if not terms:
            terms = [str((item or {}).get("term") or "").strip() for item in (glossary_items or []) if str((item or {}).get("term") or "").strip()]

        if not terms:
            return []

        existing_map: Dict[str, str] = {}
        for item in glossary_items or []:
            term = str((item or {}).get("term") or "").strip()
            explanation = str((item or {}).get("explanation") or "").strip()
            if term and term not in existing_map:
                existing_map[term] = explanation

        llm_map = self._generate_scientific_explanations_by_llm(
            terms=terms,
            story_title=story_title,
            story_content=story_content,
            target_audience=target_audience,
        )

        aligned: List[Dict[str, str]] = []
        for term in terms:
            explanation = (
                llm_map.get(term)
                or existing_map.get(term)
                or self._build_scientific_explanation(term, story_content)
            )
            aligned.append({
                "term": term,
                "explanation": self._build_scientific_explanation(term, story_content, explanation),
            })

        return aligned

    def _is_valid_science_term(self, term: str, content: str) -> bool:
        t = (term or "").strip()

        # 1. 基础长度检查
        if len(t) < 2 or len(t) > 20:
            return False

        # 2. 标点符号检查
        invalid_chars = ["\n", "\t", "，", "。", "：", ":", "、", "（", "）", "(", ")", "“", "”", '"', "'", "《", "》", "？", "！", "!", "?"]
        if any(ch in t for ch in invalid_chars):
            return False

        # 3. 非科学词汇黑名单
        if any(hint in t for hint in NON_SCIENCE_TERM_HINTS):
            return False

        # 4. 通用非术语词汇过滤
        if t in COMMON_NON_TERM_WORDS:
            return False

        # 5. 必须在原文中出现，避免幻觉
        if t not in (content or ""):
            return False

        # 6. 优先匹配明确的科学词汇列表
        if any(hint == t for hint in SCIENCE_TERM_HINTS):
            return True

        # 7. 包含科学词素的复合词判定（更严格）
        science_morphemes = [
            "力", "波", "光", "热", "电", "磁", "能", "核", "原子", "分子", "离子",
            "星", "星", "系", "云", "洞", "体", "质",
            "细", "胞", "基", "因", "蛋", "白", "酶", "菌", "毒", "膜",
            "气", "候", "生", "态", "环", "境",
            "酸", "碱", "盐", "元", "素", "化", "合",
            "温", "度", "压", "力", "密", "度", "速", "度", "频", "率",
            "相", "对", "量", "子", "理", "论", "定", "律",
        ]

        # 检查是否包含科学词素，且不是常见词汇
        has_science_morpheme = any(m in t for m in science_morphemes)
        if has_science_morpheme:
            # 额外检查：排除一些虽然包含词素但不是科学术语的词
            non_science_with_morpheme = [
                "力气", "光彩", "热门", "电灯泡", "电影", "电视", "电话",
                "星星", "明星", "精灵", "精力", "人气", "天气",
                "细心", "仔细", "基本", "根本", "素质",
            ]
            if t not in non_science_with_morpheme:
                return True

        # 8. 更严格的规则：如果以上都不匹配，只有在特定情况下才接受
        # （这里保持保守，宁可漏选也不要误选）
        return False

    def _normalize_revised_glossary(self, result: Dict[str, Any], content: str) -> List[Dict[str, str]]:
        raw_items: List[Any] = []
        for key in ("revised_glossary", "glossary"):
            value = result.get(key)
            if isinstance(value, list):
                raw_items.extend(value)

        normalized: List[Dict[str, str]] = []
        seen = set()

        def add_term(term: str, explanation: str = ""):
            clean_term = str(term or "").strip()
            if not clean_term:
                return
            key = clean_term.lower()
            if key in seen:
                return
            if not self._is_valid_science_term(clean_term, content):
                return
            seen.add(key)
            normalized.append({
                "term": clean_term,
                "explanation": self._build_scientific_explanation(clean_term, content, explanation),
            })

        for item in raw_items:
            if not isinstance(item, dict):
                continue
            add_term(str(item.get("term") or ""), str(item.get("explanation") or ""))

        # 补齐到至少 3 条：优先用高亮词，再从正文中抽取候选科学词。
        if len(normalized) < 3:
            for term in self._to_string_list(result.get("highlight_terms")):
                add_term(term)
                if len(normalized) >= 3:
                    break

        if len(normalized) < 3:
            for term in self._extract_content_terms(content, strict=True):
                add_term(term)
                if len(normalized) >= 3:
                    break

        # 文末词条限制在 3-5 条；若不足 3 条也不强行补噪声词。
        return normalized[:5]

    def _extract_content_terms(self, content: str, strict: bool = True) -> List[str]:
        text = str(content or "")
        candidates: List[str] = []

        # 优先命中已知科学词。
        for hint in SCIENCE_TERM_HINTS:
            if hint in text:
                candidates.append(hint)

        # 再从正文抽取 2-10 字中文短语。
        for match in re.finditer(r"[\u4e00-\u9fff]{2,10}", text):
            token = match.group(0).strip()
            if not token or token in COMMON_NON_TERM_WORDS:
                continue
            if strict and not self._is_valid_science_term(token, text):
                continue
            candidates.append(token)

        deduped: List[str] = []
        seen = set()
        for term in candidates:
            key = term.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(term)
        return deduped

    def _normalize_highlight_terms(self, result: Dict[str, Any], content: str, glossary_terms: List[str]) -> List[str]:
        terms = self._to_string_list(result.get("highlight_terms"))

        # Fallback to glossary terms when highlight terms are missing or too short.
        terms.extend(glossary_terms)

        # Also accept terms from both glossary fields from model output.
        for key in ("revised_glossary", "glossary"):
            value = result.get(key)
            if not isinstance(value, list):
                continue
            for item in value:
                if isinstance(item, dict):
                    terms.append(str(item.get("term") or "").strip())

        deduped: List[str] = []
        seen = set()
        for term in terms:
            key = term.lower()
            if key in seen:
                continue
            if not self._is_valid_science_term(term, content):
                continue
            seen.add(key)
            deduped.append(term)

        # 不再为了数量强行补词，避免引入不相关术语。

        # Keep a practical upper bound for UI readability.
        return deduped[:12]

    def _generate_reference_sources_by_llm(
        self,
        story_title: str,
        story_content: str,
        target_audience: str,
        highlight_terms: List[str],
        evidence_context: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, str]]:
        terms = [str(t or "").strip() for t in (highlight_terms or []) if str(t or "").strip()][:10]
        content_excerpt = str(story_content or "")[:2200]

        evidence_hints: List[str] = []
        for item in (evidence_context or [])[:6]:
            if not isinstance(item, dict):
                continue
            source = str(item.get("source_name") or "").strip()
            url = str(item.get("source_url") or "").strip()
            if source:
                evidence_hints.append(f"{source}{(' | ' + url) if url else ''}")

        system_prompt = (
            "你是一名科普事实核查编辑，负责给文章提供可执行的引用来源建议。"
            "来源建议必须具体、权威、可检索。"
            "只返回JSON。"
        )
        user_prompt = (
            "请根据以下文章信息，生成3-5条引用来源建议。\n"
            "每条建议必须包含：source_name、source_type、reason、url_hint。\n"
            "要求：\n"
            "1) source_name必须是具体机构/数据库/标准教材名称（如NASA、NOAA、FAO、IPCC、中国科学院等）；\n"
            "2) reason说明该来源可支持文中的哪类论断（数值、定义、机制、案例）；\n"
            "3) url_hint给出可检索入口（可为官网域名或数据库主页），不要编造具体论文DOI；\n"
            "4) 返回JSON格式：{\"reference_sources\":[{\"source_name\":\"\",\"source_type\":\"\",\"reason\":\"\",\"url_hint\":\"\"}]}。\n\n"
            f"标题：{story_title or '未命名故事'}\n"
            f"受众：{target_audience or '大众'}\n"
            f"高亮术语：{json.dumps(terms, ensure_ascii=False)}\n"
            f"证据来源提示：{json.dumps(evidence_hints, ensure_ascii=False)}\n"
            f"正文摘要：\n{content_excerpt}"
        )

        try:
            llm_result = llm_client.generate_json(system_prompt, user_prompt)
        except Exception:
            return []

        if not isinstance(llm_result, dict):
            return []

        raw = llm_result.get("reference_sources")
        if not isinstance(raw, list):
            return []

        normalized: List[Dict[str, str]] = []
        seen = set()
        for item in raw:
            if not isinstance(item, dict):
                continue
            source_name = str(item.get("source_name") or "").strip()
            source_type = str(item.get("source_type") or "").strip()
            reason = str(item.get("reason") or "").strip()
            url_hint = str(item.get("url_hint") or "").strip()
            if not source_name or not reason:
                continue
            key = source_name.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append({
                "source_name": source_name,
                "source_type": source_type or "权威机构/数据库",
                "reason": reason,
                "url_hint": url_hint,
            })

        return normalized[:5]

    def _fallback_reference_sources(
        self,
        evidence_context: Optional[List[Dict[str, Any]]] = None,
        highlight_terms: Optional[List[str]] = None,
    ) -> List[Dict[str, str]]:
        normalized: List[Dict[str, str]] = []
        seen = set()

        for item in (evidence_context or [])[:8]:
            if not isinstance(item, dict):
                continue
            source_name = str(item.get("source_name") or "").strip()
            source_url = str(item.get("source_url") or "").strip()
            if not source_name:
                continue
            key = source_name.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append({
                "source_name": source_name,
                "source_type": "检索证据来源",
                "reason": "可用于核对文中关键事实与术语定义。",
                "url_hint": source_url,
            })
            if len(normalized) >= 5:
                break

        # 若检索证据不可用，仍需返回可执行的权威来源建议，保证前端板块可用。
        if not normalized:
            terms_text = " ".join([str(t or "").strip() for t in (highlight_terms or [])])

            candidates = [
                {
                    "source_name": "中国科学院（CAS）",
                    "source_type": "国家科研机构",
                    "reason": "用于核对基础科学定义、机制解释与术语规范。",
                    "url_hint": "https://www.cas.cn",
                    "keywords": ["细胞", "微生物", "生态", "基因", "生物"],
                },
                {
                    "source_name": "NASA",
                    "source_type": "国际权威机构",
                    "reason": "用于核对天文与地球系统相关事实、观测数据和科普定义。",
                    "url_hint": "https://www.nasa.gov",
                    "keywords": ["宇宙", "卫星", "行星", "太阳", "气候", "大气"],
                },
                {
                    "source_name": "NOAA",
                    "source_type": "国际权威机构",
                    "reason": "用于核对气候、海洋与大气相关数据及长期变化趋势。",
                    "url_hint": "https://www.noaa.gov",
                    "keywords": ["气候", "海洋", "温度", "碳循环", "大气", "风"],
                },
                {
                    "source_name": "FAO",
                    "source_type": "联合国机构",
                    "reason": "用于核对农业、生态系统与碳汇/固碳相关统计口径。",
                    "url_hint": "https://www.fao.org",
                    "keywords": ["固碳", "碳", "森林", "农业", "生态"],
                },
                {
                    "source_name": "IPCC",
                    "source_type": "国际评估机构",
                    "reason": "用于核对温室气体、气候变化机制及相关量化结论。",
                    "url_hint": "https://www.ipcc.ch",
                    "keywords": ["温室效应", "全球变暖", "碳", "气候"],
                },
            ]

            for item in candidates:
                source_name = item["source_name"]
                key = source_name.lower()
                if key in seen:
                    continue
                keywords = item.get("keywords", [])
                if keywords and terms_text and not any(k in terms_text for k in keywords):
                    continue
                seen.add(key)
                normalized.append({
                    "source_name": source_name,
                    "source_type": item["source_type"],
                    "reason": item["reason"],
                    "url_hint": item["url_hint"],
                })
                if len(normalized) >= 5:
                    break

        # 若关键词匹配后仍为空，则给出通用三条兜底。
        if not normalized:
            normalized = [
                {
                    "source_name": "中国科学院（CAS）",
                    "source_type": "国家科研机构",
                    "reason": "用于核对基础科学概念、术语定义与机制解释。",
                    "url_hint": "https://www.cas.cn",
                },
                {
                    "source_name": "国家自然科学基金委员会（NSFC）科普资源",
                    "source_type": "国家科研管理机构",
                    "reason": "用于检索中文科研背景材料与规范术语表述。",
                    "url_hint": "https://www.nsfc.gov.cn",
                },
                {
                    "source_name": "科普中国",
                    "source_type": "国家级科普平台",
                    "reason": "用于核对面向大众的科学解释与科普表达是否准确。",
                    "url_hint": "https://www.kepuchina.cn",
                },
            ]

        return normalized

    def _inject_reference_section(
        self,
        result: Dict[str, Any],
        reference_sources: List[Dict[str, str]],
    ) -> None:
        if not isinstance(result.get("review_sections"), list):
            return

        if not reference_sources:
            return

        lines = []
        for idx, item in enumerate(reference_sources, 1):
            source_name = item.get("source_name", "")
            source_type = item.get("source_type", "")
            reason = item.get("reason", "")
            url_hint = item.get("url_hint", "")
            line = f"{idx}. {source_name}（{source_type}）：{reason}"
            if url_hint:
                line += f"；检索入口：{url_hint}"
            lines.append(line)

        finding_text = "建议补充以下引用来源以支撑关键论断。"
        suggestion_text = "；".join(lines)
        revision_text = "\n".join([f"- {line}" for line in lines])

        sections = result.get("review_sections", [])
        for section in sections:
            if not isinstance(section, dict):
                continue
            section_name = str(section.get("section") or "")
            if section_name == "引用来源建议":
                section["status"] = "建议补充"
                section["finding"] = finding_text
                section["suggestion"] = suggestion_text
                section["suggested_revision"] = revision_text
                section["issue_list"] = lines
                section["modification_list"] = []
                section["adopted"] = False
                break

    def _detect_section(self, text: str) -> str:
        normalized = text.strip()
        for section, keywords in SECTION_KEYWORDS.items():
            if any(keyword in normalized for keyword in keywords):
                return section

        # 默认优先归到事实校验，避免关键问题丢失
        return "事实准确性校验"

    def _build_structured_sections(self, issues: List[str], modifications: List[str]) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, List[str]]] = {
            section: {"issues": [], "modifications": []} for section in SECTION_ORDER
        }

        for issue in issues:
            grouped[self._detect_section(issue)]["issues"].append(issue)

        for mod in modifications:
            grouped[self._detect_section(mod)]["modifications"].append(mod)

        sections: List[Dict[str, Any]] = []
        for section in SECTION_ORDER:
            section_issues = grouped[section]["issues"]
            section_mods = grouped[section]["modifications"]

            if section_issues:
                finding = "；".join(section_issues)
                suggestion = f"建议优先修正以下问题：{'；'.join(section_issues)}"
                status = "需修正"
            elif section_mods:
                finding = f"已完成修订：{'；'.join(section_mods)}"
                suggestion = f"建议保持当前修订方向，并复查相关段落：{'；'.join(section_mods)}"
                status = "通过"
            else:
                finding = "未发现明显问题"
                suggestion = "建议保持当前表达，并在终稿阶段做一次复核。"
                status = "通过"

            sections.append({
                "section": section,
                "status": status,
                "finding": finding,
                "suggestion": suggestion,
                "suggested_revision": "；".join(section_mods) if section_mods else "无需改写",
                "issue_list": section_issues,
                "modification_list": section_mods,
                "adopted": len(section_mods) > 0,
            })

        return sections

    def _post_process_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        issues = self._to_string_list(result.get("issues"))
        modifications = self._to_string_list(result.get("modifications_made"))
        content = str(result.get("revised_content") or "")
        if not content.strip():
            content = str(result.get("content") or "")

        # 合并 DeepSearch 词条候选，增强高亮词条与文末词条稳定性。
        deepsearch_terms = result.get("deepsearch_glossary_candidates")
        if isinstance(deepsearch_terms, list) and deepsearch_terms:
            merged_revised = result.get("revised_glossary")
            if not isinstance(merged_revised, list):
                merged_revised = []
            merged_glossary = result.get("glossary")
            if not isinstance(merged_glossary, list):
                merged_glossary = []
            merged = [*merged_revised, *merged_glossary, *deepsearch_terms]
            result["revised_glossary"] = merged
            result["glossary"] = merged

        normalized_glossary = self._normalize_revised_glossary(result, content)
        glossary_terms = [item["term"] for item in normalized_glossary]
        highlight_terms = self._normalize_highlight_terms(result, content, glossary_terms)

        result["issues"] = issues
        result["modifications_made"] = modifications
        result["glossary"] = normalized_glossary
        result["revised_glossary"] = normalized_glossary
        result["highlight_terms"] = highlight_terms
        result["review_sections"] = self._build_structured_sections(issues, modifications)

        if not isinstance(result.get("suggestions"), str) or not result.get("suggestions", "").strip():
            lines = []
            for section in result["review_sections"]:
                lines.append(f"{section['section']}：{section['finding']}。{section['suggestion']}")
            result["suggestions"] = "\n".join(lines)

        result["evidence_used"] = self._normalize_evidence_used(result.get("evidence_used"))

        if not isinstance(result.get("deepsearch_analysis"), dict):
            result["deepsearch_analysis"] = {}

        return result

    def run(
        self,
        story_title: str,
        story_content: str,
        target_audience: str = "大众",
        evidence_context: Optional[List[Dict[str, Any]]] = None,
        deepsearch_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        审核文本中的知识错误点，并提取专业词汇表。
        """
        evidence_context = evidence_context or []
        deepsearch_context = deepsearch_context or {}
        evidence_block = ""
        if evidence_context:
            lines = []
            for item in evidence_context[:8]:
                lines.append(
                    f"- [{item.get('evidence_id', 'E')}] 来源:{item.get('source_name', '未知来源')}"
                    f" | 权威级:{item.get('authority_level', 0)}"
                    f" | 摘录:{item.get('snippet', '')}"
                )
            evidence_block = "\n【FACT证据包（必须优先引用）】：\n" + "\n".join(lines)

        deepsearch_analysis = deepsearch_context.get("analysis_4d") if isinstance(deepsearch_context, dict) else {}
        deepsearch_glossary_candidates = (
            deepsearch_context.get("glossary_candidates") if isinstance(deepsearch_context, dict) else []
        )
        deepsearch_block = ""
        if isinstance(deepsearch_analysis, dict) and deepsearch_analysis:
            ds_lines = []
            for section in SECTION_ORDER:
                value = deepsearch_analysis.get(section)
                if isinstance(value, list):
                    value_text = "；".join([str(v).strip() for v in value if str(v).strip()])
                else:
                    value_text = str(value or "").strip()
                if value_text:
                    ds_lines.append(f"- {section}：{value_text}")
            if ds_lines:
                deepsearch_block = "\n【DeepSearch四维分析（优先参考）】：\n" + "\n".join(ds_lines)

        user_prompt = SCIENCE_CHECKER_USER_PROMPT_TEMPLATE.format(
            target_audience=target_audience,
            story_title=story_title,
            story_content=story_content,
            evidence_block=evidence_block,
            deepsearch_block=deepsearch_block,
        )

        # 调用大模型生成JSON结果
        raw_result = llm_client.generate_json(self.system_prompt, user_prompt)
        if not isinstance(raw_result, dict):
            raw_result = {}

        raw_result["deepsearch_analysis"] = deepsearch_analysis if isinstance(deepsearch_analysis, dict) else {}
        raw_result["deepsearch_glossary_candidates"] = (
            deepsearch_glossary_candidates if isinstance(deepsearch_glossary_candidates, list) else []
        )

        self.result = self._post_process_result(raw_result)

        aligned_glossary = self._align_glossary_with_highlight_terms(
            highlight_terms=self._to_string_list(self.result.get("highlight_terms")),
            glossary_items=self.result.get("revised_glossary") if isinstance(self.result.get("revised_glossary"), list) else [],
            story_title=story_title,
            story_content=str(self.result.get("revised_content") or story_content or ""),
            target_audience=target_audience,
        )
        if aligned_glossary:
            self.result["glossary"] = aligned_glossary
            self.result["revised_glossary"] = aligned_glossary

        reference_sources = self._generate_reference_sources_by_llm(
            story_title=story_title,
            story_content=str(self.result.get("revised_content") or story_content or ""),
            target_audience=target_audience,
            highlight_terms=self._to_string_list(self.result.get("highlight_terms")),
            evidence_context=evidence_context,
        )
        if not reference_sources:
            reference_sources = self._fallback_reference_sources(
                evidence_context=evidence_context,
                highlight_terms=self._to_string_list(self.result.get("highlight_terms")),
            )

        if reference_sources:
            self.result["reference_sources"] = reference_sources
            self._inject_reference_section(self.result, reference_sources)

        # 若模型未显式回填证据，则自动带回检索证据，保证审查可追溯。
        if evidence_context and not self.result.get("evidence_used"):
            self.result["evidence_used"] = evidence_context[:5]

        return self.result
