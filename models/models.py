from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Float
from sqlalchemy.sql import func
from utils.database import Base

class Story(Base):
    """创作故事记录表"""
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    theme = Column(String(100), nullable=False)           # 题材/关键词
    age_group = Column(String(20), nullable=False)        # 年龄段
    style = Column(String(100), nullable=True)            # 文章风格
    target_audience = Column(String(200), nullable=True)  # 科普对象（如农民、老年人等）
    extra_requirements = Column(String(500), nullable=True) # 用户自主设定的额外要求
    content = Column(Text, nullable=True)                 # 生成的文本故事
    glossary = Column(Text, nullable=True)                # 提取的专业术语及解释(JSON字符串)
    status = Column(Integer, default=0)                   # 状态 0:建档 1:生成中 2:审核中 3:完成
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    llm_text_provider = Column(String(32), nullable=True)
    llm_text_api_key = Column(String(512), nullable=True)
    llm_image_provider = Column(String(32), nullable=True)
    llm_image_api_key = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class UserToken(Base):
    """用户会话token表（仅存哈希）"""
    __tablename__ = "user_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    token_hash = Column(String(128), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class AgentFeedback(Base):
    """智能体反馈表"""
    __tablename__ = "agent_feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    story_id = Column(Integer, ForeignKey("stories.id"))
    agent_type = Column(String(50))   # science_checker, reader, illustrator
    feedback = Column(Text)           # 反馈意见或JSON字符串
    created_at = Column(DateTime, server_default=func.now())


class KnowledgeDocument(Base):
    """RAG知识文档表（支持FACT/STYLE双轨，阶段1先用FACT）"""
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(255), nullable=False)
    source_url = Column(String(1024), nullable=True)
    publisher = Column(String(255), nullable=True)
    author = Column(String(255), nullable=True)           # 新增：作者
    publish_year = Column(Integer, nullable=True)          # 新增：出版年份
    authority_level = Column(Integer, default=80)  # 0-100
    doc_type = Column(String(20), default="FACT")
    topic_tags = Column(Text, nullable=True)       # JSON字符串
    audience_tags = Column(Text, nullable=True)    # JSON字符串
    style_tags = Column(Text, nullable=True)       # 新增：风格标签 JSON字符串
    award_tags = Column(Text, nullable=True)       # 新增：奖项标签 JSON字符串
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class KnowledgeChunk(Base):
    """RAG知识分块表（用于混合检索）"""
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id"), index=True, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    keywords = Column(Text, nullable=True)         # JSON字符串
    embedding = Column(Text, nullable=True)        # JSON字符串
    created_at = Column(DateTime, server_default=func.now())


# =============== 知识图谱模型 ===============

ENTITY_TYPES = {
    "CONCEPT": "科学概念",
    "OBJECT": "物体/物质",
    "ORGANISM": "生物",
    "PERSON": "人物",
    "PLANET": "星球",
    "PHENOMENON": "自然现象",
    "PROCESS": "过程/原理",
    "DEVICE": "设备/工具",
    "PLACE": "地点",
    "EVENT": "事件",
}

RELATION_TYPES = {
    "IS_A": "是一种",
    "PART_OF": "是...的一部分",
    "HAS_PART": "包含",
    "CAUSES": "导致",
    "IS_CAUSED_BY": "由...导致",
    "RELATED_TO": "与...相关",
    "INTERACTS_WITH": "与...相互作用",
    "LIVES_IN": "生活在",
    "DISCOVERED_BY": "由...发现",
    "EXAMPLE_OF": "是...的例子",
    "SIMILAR_TO": "类似于",
    "CONTRASTS_WITH": "与...形成对比",
}


class KnowledgeGraphEntity(Base):
    """知识图谱实体表"""
    __tablename__ = "kg_entities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    aliases = Column(Text, nullable=True)          # JSON数组
    properties = Column(Text, nullable=True)       # JSON对象
    source_document_id = Column(Integer, ForeignKey("knowledge_documents.id"), nullable=True)
    confidence = Column(Float, default=0.8)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class KnowledgeGraphRelation(Base):
    """知识图谱关系表"""
    __tablename__ = "kg_relations"

    id = Column(Integer, primary_key=True, index=True)
    source_entity_id = Column(Integer, ForeignKey("kg_entities.id"), nullable=False, index=True)
    target_entity_id = Column(Integer, ForeignKey("kg_entities.id"), nullable=False, index=True)
    relation_type = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    properties = Column(Text, nullable=True)       # JSON对象
    source_document_id = Column(Integer, ForeignKey("knowledge_documents.id"), nullable=True)
    confidence = Column(Float, default=0.8)
    created_at = Column(DateTime, server_default=func.now())


class KnowledgeGraphEntityEmbedding(Base):
    """实体向量嵌入表（用于语义搜索）"""
    __tablename__ = "kg_entity_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("kg_entities.id"), nullable=False, unique=True, index=True)
    embedding = Column(Text, nullable=False)      # JSON数组
    updated_at = Column(DateTime, onupdate=func.now())
