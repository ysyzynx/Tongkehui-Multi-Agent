"""
KidsSci-Store - 儿童科普专用知识库
基于 OpenScholar 的 OSDS (OpenScholar DataStore)

注意：这是框架实现，暂时不填充实际内容
"""
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session


class KnowledgeSourceType(Enum):
    """知识来源类型"""
    TEXTBOOK = "textbook"              # 教材
    POPULAR_SCIENCE = "popular_science"  # 科普图书
    WEBSITE = "website"                # 科普网站
    ENCYCLOPEDIA = "encyclopedia"      # 百科全书
    ACADEMIC = "academic"              # 学术论文（摘要）
    OTHER = "other"                    # 其他


class AgeRange(Enum):
    """目标年龄段"""
    AGE_5_7 = "5-7"
    AGE_8_12 = "8-12"
    AGE_13_16 = "13-16"
    ALL = "all"


class ScienceTopic(Enum):
    """科学主题分类"""
    ASTRONOMY = "astronomy"              # 天文学
    BIOLOGY = "biology"                  # 生物学
    CHEMISTRY = "chemistry"              # 化学
    PHYSICS = "physics"                  # 物理学
    EARTH_SCIENCE = "earth_science"      # 地球科学
    ECOLOGY = "ecology"                  # 生态学
    PALEONTOLOGY = "paleontology"        # 古生物学
    TECHNOLOGY = "technology"            # 科技
    GENERAL = "general"                  # 综合


@dataclass
class KnowledgeChunk:
    """知识片段（用于检索的最小单位）"""
    chunk_id: str
    document_id: str
    chunk_index: int
    chunk_text: str
    keywords: List[str]
    embedding: Optional[List[float]] = None
    score: Optional[float] = None


@dataclass
class KnowledgeDocument:
    """知识文档"""
    document_id: str
    source_name: str
    source_type: KnowledgeSourceType
    source_url: Optional[str]
    publisher: Optional[str]
    author: Optional[str]
    publish_year: Optional[int]
    authority_level: int  # 0-100
    topics: List[ScienceTopic]
    age_ranges: List[AgeRange]
    title: str
    description: Optional[str]
    content: str
    chunks: List[KnowledgeChunk]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class KidsSciStore:
    """
    儿童科普专用知识库

    设计参考 OpenScholar 的 OSDS：
    - 领域专用：专注儿童科普
    - 年龄段分级：5-7, 8-12, 13-16
    - 主题分类：天文学、生物学、物理学等
    - 权威度分级：教材 > 百科 > 科普图书 > 网站
    """

    # 默认配置
    DEFAULT_CHUNK_SIZE = 300      # 每个知识片段的字符数
    DEFAULT_CHUNK_OVERLAP = 50    # 片段重叠字符数
    DEFAULT_TOP_K = 5             # 默认返回结果数
    MIN_AUTHORITY_LEVEL = 60      # 最低权威度要求

    # 主题关键词映射（用于自动分类）
    TOPIC_KEYWORDS = {
        ScienceTopic.ASTRONOMY: [
            "太阳", "恒星", "行星", "卫星", "彗星", "黑洞", "银河", "宇宙",
            "星系", "星云", "星团", "超新星", "日食", "月食", "潮汐",
            "太阳系", "银河系", "小行星", "流星", "陨石", "天文台", "望远镜",
            "地球", "月亮", "火星", "木星", "土星", "金星", "水星", "天王星", "海王星",
        ],
        ScienceTopic.BIOLOGY: [
            "细胞", "细胞膜", "细胞核", "细胞质", "细胞壁", "叶绿体", "线粒体",
            "DNA", "RNA", "基因", "染色体", "遗传", "变异", "进化", "进化论",
            "微生物", "细菌", "病毒", "真菌", "原生生物", "细胞分裂", "有丝分裂",
            "新陈代谢", "光合作用", "呼吸作用", "消化", "循环", "神经", "激素",
            "生态", "生态系统", "种群", "群落", "食物链", "食物网", "生产者",
            "消费者", "分解者", "生物圈", "栖息地", "生物多样性", "物种", "灭绝",
            "根", "茎", "叶", "花", "果实", "种子", "授粉", "发芽",
            "心脏", "肺", "胃", "肠", "肝", "肾", "脑", "神经", "肌肉", "骨骼",
            "动物", "植物", "昆虫", "鸟类", "哺乳动物", "爬行动物", "两栖动物",
        ],
        ScienceTopic.CHEMISTRY: [
            "元素", "化合物", "混合物", "原子", "分子", "离子", "化学键",
            "酸", "碱", "盐", "pH值", "氧化", "还原", "催化剂", "反应",
            "金属", "非金属", "有机物", "无机物", "晶体", "溶液", "溶解", "沉淀",
            "碳", "氢", "氧", "氮", "钙", "铁", "锌", "钾", "钠", "镁",
        ],
        ScienceTopic.PHYSICS: [
            "引力", "重力", "万有引力", "速度", "加速度", "动能", "势能", "能量", "功",
            "光", "光子", "光线", "光源", "光速", "反射", "折射", "散射", "色散",
            "电磁波", "波长", "频率", "辐射", "红外线", "紫外线", "可见光", "X射线",
            "温度", "压强", "密度", "体积", "质量", "重量", "力", "牛顿", "焦耳",
            "电", "电流", "电压", "电阻", "电路", "磁铁", "磁场", "电磁感应",
            "原子", "分子", "离子", "电子", "质子", "中子", "原子核", "粒子",
            "核聚变", "核裂变", "核反应", "放射性", "同位素", "量子", "相对论",
            "声", "声音", "声波", "频率", "振幅", "超声波", "次声波",
            "热", "热量", "传导", "对流", "辐射", "熔点", "沸点", "凝固", "蒸发",
        ],
        ScienceTopic.EARTH_SCIENCE: [
            "大气", "大气层", "气候", "天气", "温度", "湿度", "气压", "风",
            "云", "雨", "雪", "冰雹", "霜", "露", "雾", "台风", "飓风",
            "地壳", "地幔", "地核", "板块", "地震", "火山", "岩浆", "岩石",
            "矿物", "化石", "土壤", "侵蚀", "沉积", "变质", "山脉", "峡谷",
            "海洋", "河流", "湖泊", "冰川", "地下水", "水循环", "碳循环",
            "地球", "大陆", "岛屿", "半岛", "海峡", "海湾",
        ],
        ScienceTopic.PALEONTOLOGY: [
            "恐龙", "化石", "古生物", "三叠纪", "侏罗纪", "白垩纪",
            "霸王龙", "腕龙", "三角龙", "剑龙", "翼龙", "蛇颈龙",
            "灭绝", "史前", "古生代", "中生代", "新生代",
        ],
        ScienceTopic.TECHNOLOGY: [
            "科技", "技术", "发明", "机器人", "人工智能", "计算机", "互联网",
            "火箭", "卫星", "航天", "太空站", "探测器",
            "纳米", "基因工程", "克隆", "疫苗", "抗生素",
        ],
    }

    # 非科学关键词（用于过滤）
    NON_SCIENCE_KEYWORDS = [
        "小朋友", "小明", "小红", "老师", "博士", "妈妈", "爸爸",
        "故事", "冒险", "奇遇", "魔法", "精灵", "勇士",
        "开心", "快乐", "惊讶", "害怕", "神奇", "美妙",
    ]

    def __init__(self, db_session: Optional[Session] = None):
        self.db_session = db_session
        self._documents: Dict[str, KnowledgeDocument] = {}  # 内存存储（框架用）
        self._chunks: Dict[str, KnowledgeChunk] = {}
        self._chunk_index: List[Dict[str, Any]] = []  # 简单索引

    def is_initialized(self) -> bool:
        """检查知识库是否已初始化并填充内容"""
        return len(self._documents) > 0

    def get_initialization_status(self) -> Dict[str, Any]:
        """获取知识库初始化状态"""
        return {
            "is_initialized": self.is_initialized(),
            "document_count": len(self._documents),
            "chunk_count": len(self._chunks),
            "topics": list(set([t.value for d in self._documents.values() for t in d.topics])),
            "age_ranges": list(set([a.value for d in self._documents.values() for a in d.age_ranges])),
            "message": "这是框架实现，暂时没有填充实际内容。请添加教材、科普图书等资料。" if not self.is_initialized() else "知识库已就绪。",
        }

    # ========== 文档管理 ==========

    def add_document(
        self,
        source_name: str,
        source_type: str,
        content: str,
        title: Optional[str] = None,
        source_url: Optional[str] = None,
        publisher: Optional[str] = None,
        author: Optional[str] = None,
        publish_year: Optional[int] = None,
        authority_level: Optional[int] = None,
        topics: Optional[List[str]] = None,
        age_ranges: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> str:
        """
        添加文档到知识库

        参数:
            source_name: 来源名称（如"人教版小学科学三年级"）
            source_type: 来源类型（textbook/popular_science/website/encyclopedia/academic）
            content: 文档内容
            title: 文档标题
            source_url: 来源URL
            publisher: 出版社
            author: 作者
            publish_year: 出版年份
            authority_level: 权威度（0-100，不传则自动估算）
            topics: 主题列表（不传则自动分类）
            age_ranges: 年龄段列表（不传则默认 ["8-12"]）
            description: 文档描述

        返回:
            document_id
        """
        import uuid
        document_id = str(uuid.uuid4())

        # 解析枚举
        source_type_enum = self._parse_source_type(source_type)
        topics_enum = self._parse_topics(topics or self._classify_topics(content))
        age_ranges_enum = self._parse_age_ranges(age_ranges or ["8-12"])

        # 自动估算权威度
        if authority_level is None:
            authority_level = self._estimate_authority_level(source_type_enum, publisher)

        # 切分内容为片段
        chunks = self._split_content_into_chunks(
            content,
            document_id,
            chunk_size=self.DEFAULT_CHUNK_SIZE,
            overlap=self.DEFAULT_CHUNK_OVERLAP,
        )

        # 创建文档对象
        doc = KnowledgeDocument(
            document_id=document_id,
            source_name=source_name,
            source_type=source_type_enum,
            source_url=source_url,
            publisher=publisher,
            author=author,
            publish_year=publish_year,
            authority_level=authority_level,
            topics=topics_enum,
            age_ranges=age_ranges_enum,
            title=title or source_name,
            description=description,
            content=content,
            chunks=chunks,
        )

        # 存储（内存中）
        self._documents[document_id] = doc
        for chunk in chunks:
            self._chunks[chunk.chunk_id] = chunk
            self._chunk_index.append({
                "chunk_id": chunk.chunk_id,
                "document_id": document_id,
                "text": chunk.chunk_text,
                "keywords": chunk.keywords,
                "topics": [t.value for t in doc.topics],
                "age_ranges": [a.value for a in doc.age_ranges],
                "authority_level": doc.authority_level,
            })

        return document_id

    def get_document(self, document_id: str) -> Optional[KnowledgeDocument]:
        """获取文档"""
        return self._documents.get(document_id)

    def list_documents(
        self,
        topic: Optional[str] = None,
        age_range: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """列出文档"""
        docs = list(self._documents.values())

        if topic:
            topic_enum = self._parse_topics([topic])[0]
            docs = [d for d in docs if topic_enum in d.topics]

        if age_range:
            age_enum = self._parse_age_ranges([age_range])[0]
            docs = [d for d in docs if age_enum in d.age_ranges]

        if source_type:
            st_enum = self._parse_source_type(source_type)
            docs = [d for d in docs if d.source_type == st_enum]

        return [
            {
                "document_id": d.document_id,
                "source_name": d.source_name,
                "source_type": d.source_type.value,
                "title": d.title,
                "authority_level": d.authority_level,
                "topics": [t.value for t in d.topics],
                "age_ranges": [a.value for a in d.age_ranges],
                "chunk_count": len(d.chunks),
            }
            for d in docs[:limit]
        ]

    # ========== 检索功能 ==========

    def search(
        self,
        query: str,
        topic: Optional[str] = None,
        age_range: Optional[str] = "8-12",
        top_k: int = 5,
        min_authority_level: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        检索知识库

        参数:
            query: 检索查询
            topic: 主题过滤
            age_range: 年龄段过滤
            top_k: 返回结果数
            min_authority_level: 最低权威度

        返回:
            检索结果列表
        """
        if not self.is_initialized():
            return []

        min_auth = min_authority_level or self.MIN_AUTHORITY_LEVEL

        # 简单关键词匹配（框架实现，实际可用向量检索）
        query_words = self._extract_keywords(query)

        results = []
        for idx_info in self._chunk_index:
            # 过滤
            if age_range and age_range not in idx_info["age_ranges"]:
                continue
            if topic and topic not in idx_info["topics"]:
                continue
            if idx_info["authority_level"] < min_auth:
                continue

            # 简单匹配评分
            chunk_words = set(idx_info["keywords"])
            overlap = len(set(query_words).intersection(chunk_words))
            if overlap == 0:
                continue

            score = overlap / max(1, len(query_words))
            authority_bonus = idx_info["authority_level"] / 100.0
            final_score = 0.6 * score + 0.4 * authority_bonus

            results.append({
                "chunk_id": idx_info["chunk_id"],
                "document_id": idx_info["document_id"],
                "source_name": self._documents[idx_info["document_id"]].source_name,
                "snippet": idx_info["text"][:200],
                "authority_level": idx_info["authority_level"],
                "score": round(final_score, 4),
                "topics": idx_info["topics"],
            })

        # 排序并返回 top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    # ========== 内部辅助方法 ==========

    def _parse_source_type(self, source_type: str) -> KnowledgeSourceType:
        """解析来源类型"""
        mapping = {
            "textbook": KnowledgeSourceType.TEXTBOOK,
            "popular_science": KnowledgeSourceType.POPULAR_SCIENCE,
            "website": KnowledgeSourceType.WEBSITE,
            "encyclopedia": KnowledgeSourceType.ENCYCLOPEDIA,
            "academic": KnowledgeSourceType.ACADEMIC,
        }
        return mapping.get(source_type.lower(), KnowledgeSourceType.OTHER)

    def _parse_topics(self, topics: List[str]) -> List[ScienceTopic]:
        """解析主题"""
        result = []
        for topic in topics:
            for enum_topic in ScienceTopic:
                if enum_topic.value == topic.lower():
                    result.append(enum_topic)
                    break
        return result or [ScienceTopic.GENERAL]

    def _parse_age_ranges(self, age_ranges: List[str]) -> List[AgeRange]:
        """解析年龄段"""
        result = []
        for age in age_ranges:
            for enum_age in AgeRange:
                if enum_age.value == age:
                    result.append(enum_age)
                    break
        return result or [AgeRange.AGE_8_12]

    def _estimate_authority_level(
        self,
        source_type: KnowledgeSourceType,
        publisher: Optional[str] = None,
    ) -> int:
        """估算权威度"""
        base_scores = {
            KnowledgeSourceType.TEXTBOOK: 90,
            KnowledgeSourceType.ENCYCLOPEDIA: 85,
            KnowledgeSourceType.POPULAR_SCIENCE: 80,
            KnowledgeSourceType.ACADEMIC: 75,
            KnowledgeSourceType.WEBSITE: 65,
            KnowledgeSourceType.OTHER: 60,
        }

        base = base_scores.get(source_type, 60)

        # 知名出版社加分
        reputable_publishers = [
            "人民教育出版社", "人教版", "商务印书馆", "中国大百科全书出版社",
            "科学出版社", "少年儿童出版社", "中国少年儿童出版社",
        ]
        if publisher and any(p in publisher for p in reputable_publishers):
            base += 5

        return min(100, base)

    def _classify_topics(self, content: str) -> List[str]:
        """自动分类主题"""
        content_lower = content.lower()
        topics = []

        for topic, keywords in self.TOPIC_KEYWORDS.items():
            if any(k in content_lower for k in keywords):
                topics.append(topic.value)

        return topics or ["general"]

    def _split_content_into_chunks(
        self,
        content: str,
        document_id: str,
        chunk_size: int = 300,
        overlap: int = 50,
    ) -> List[KnowledgeChunk]:
        """切分内容为片段"""
        import uuid

        # 先按段落分割
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", content) if p.strip()]
        if not paragraphs:
            paragraphs = [content]

        chunks = []
        chunk_index = 0

        for para in paragraphs:
            if len(para) <= chunk_size:
                keywords = self._extract_keywords(para)
                chunks.append(KnowledgeChunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document_id,
                    chunk_index=chunk_index,
                    chunk_text=para,
                    keywords=keywords,
                ))
                chunk_index += 1
            else:
                # 长段落需要进一步切分
                start = 0
                while start < len(para):
                    end = min(len(para), start + chunk_size)
                    chunk_text = para[start:end].strip()
                    keywords = self._extract_keywords(chunk_text)
                    chunks.append(KnowledgeChunk(
                        chunk_id=str(uuid.uuid4()),
                        document_id=document_id,
                        chunk_index=chunk_index,
                        chunk_text=chunk_text,
                        keywords=keywords,
                    ))
                    chunk_index += 1
                    start = max(0, end - overlap)

        return chunks

    def _extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """提取关键词（简单实现）"""
        # 移除非科学关键词
        for word in self.NON_SCIENCE_KEYWORDS:
            text = text.replace(word, "")

        # 提取2-4字的词
        tokens = re.findall(r"[\u4e00-\u9fff]{2,4}", text)

        # 简单频率统计
        freq: Dict[str, int] = {}
        for token in tokens:
            freq[token] = freq.get(token, 0) + 1

        # 排序并返回 top_k
        sorted_tokens = sorted(freq.items(), key=lambda x: (-x[1], -len(x[0])))
        return [t[0] for t in sorted_tokens[:top_k]]


# 单例
_kids_sci_store_instance: Optional[KidsSciStore] = None


def get_kids_sci_store(db_session: Optional[Session] = None) -> KidsSciStore:
    """获取 KidsSciStore 单例"""
    global _kids_sci_store_instance
    if _kids_sci_store_instance is None:
        _kids_sci_store_instance = KidsSciStore(db_session=db_session)
    elif db_session is not None:
        _kids_sci_store_instance.db_session = db_session
    return _kids_sci_store_instance
