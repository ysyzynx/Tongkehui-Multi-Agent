from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# --------------- Auth Schemas ---------------
class AuthRegisterRequest(BaseModel):
    username: str
    password: str


class AuthLoginRequest(BaseModel):
    username: str
    password: str


class AuthUserInfo(BaseModel):
    id: int
    username: str


class AuthTokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: AuthUserInfo

# --------------- Story Schemas ---------------
class StoryCreateRequest(BaseModel):
    project_title: Optional[str] = None
    theme: Optional[str] = None
    age_group: Optional[str] = None
    style: Optional[str] = None
    target_audience: Optional[str] = None
    extra_requirements: Optional[str] = None
    word_count: Optional[int] = 1200
    use_rag: Optional[bool] = True  # 是否使用RAG知识库
    use_fact_rag: Optional[bool] = None  # 与科学审查页一致命名，优先于use_rag
    use_deepsearch: Optional[bool] = False
    deepsearch_top_k: Optional[int] = 6
    rag_doc_type: Optional[str] = "SCIENCE_FACT"  # RAG知识库类型: SCIENCE_FACT(科学事实)/FACT(通用)
    rag_top_k: Optional[int] = 4  # 检索返回的证据数量
    selected_rag_ids: Optional[List[int]] = None  # 用户选中的知识库文档ID列表（仅使用这些文档）


class StorySuggestTitlesRequest(BaseModel):
    theme: str
    target_audience: Optional[str] = None
    age_group: Optional[str] = None


class LLMConfigUpdateRequest(BaseModel):
    provider: Optional[str] = Field(default=None, description="兼容旧字段：文本 provider")
    api_key: Optional[str] = None
    text_provider: Optional[str] = Field(default=None, description="文本模型供应商：qwen|volcengine|hunyuan|deepseek|wenxin")
    text_api_key: Optional[str] = None
    image_provider: Optional[str] = Field(default=None, description="绘画模型供应商：volcengine|qwen")
    image_api_key: Optional[str] = None

class StoryResponse(BaseModel):
    id: int
    title: str
    content: str
    glossary: Optional[List[Dict[str, str]]] = None

# --------------- Check Schemas ---------------
class CheckRequest(BaseModel):
    story_id: int
    title: Optional[str] = None
    content: str
    target_audience: Optional[str] = None
    use_fact_rag: Optional[bool] = True  # 默认开启RAG
    evidence_top_k: Optional[int] = 6
    rag_doc_type: Optional[str] = "SCIENCE_FACT"  # 科学审查者使用教材/权威资料库
    use_deepsearch: Optional[bool] = True
    deepsearch_top_k: Optional[int] = 6

class CheckResponse(BaseModel):
    passed: bool
    issues: Optional[List[str]] = None
    modifications_made: Optional[List[str]] = None
    suggestions: str
    review_sections: Optional[List[Dict[str, Any]]] = None
    highlight_terms: Optional[List[str]] = None
    revised_content: Optional[str] = None
    glossary: Optional[List[Dict[str, str]]] = None
    revised_glossary: Optional[List[Dict[str, str]]] = None
    evidence_used: Optional[List[Dict[str, Any]]] = None
    deepsearch_analysis: Optional[Dict[str, Any]] = None


class ScienceSelectedSection(BaseModel):
    section: str
    suggestion: Optional[str] = None
    suggested_revision: Optional[str] = None
    issue_list: Optional[List[str]] = None
    modification_list: Optional[List[str]] = None


class ScienceApplySelectedRequest(BaseModel):
    story_id: int
    title: Optional[str] = None
    content: str
    target_audience: Optional[str] = None
    selected_sections: List[ScienceSelectedSection] = Field(default_factory=list)


class ScienceApplySelectedResponse(BaseModel):
    revised_content: str
    adopted_sections: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class FactIngestRequest(BaseModel):
    source_name: str
    source_url: Optional[str] = None
    publisher: Optional[str] = None
    authority_level: Optional[int] = 80
    doc_type: Optional[str] = "FACT"  # 文档类型: SCIENCE_FACT(审查者库)/FACT(通用)
    topic_tags: Optional[List[str]] = None
    audience_tags: Optional[List[str]] = None
    content: str


class FactSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5


# --------------- Wikipedia Schemas ---------------
class WikipediaSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5
    language: Optional[str] = "zh"


class WikipediaIngestRequest(BaseModel):
    query: str
    doc_type: Optional[str] = "SCIENCE_FACT"
    authority_level: Optional[int] = 90
    limit: Optional[int] = 3
    language: Optional[str] = "zh"
    publisher: Optional[str] = "维基百科"


class WikipediaIngestByIdRequest(BaseModel):
    pageid: Optional[int] = None
    title: Optional[str] = None
    doc_type: Optional[str] = "SCIENCE_FACT"
    authority_level: Optional[int] = 90
    language: Optional[str] = "zh"
    publisher: Optional[str] = "维基百科"


# --------------- SerpAPI (谷歌学术) Schemas ---------------
class SerpAPISearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5
    language: Optional[str] = "zh-CN"


class SerpAPIIngestRequest(BaseModel):
    query: str
    doc_type: Optional[str] = "SCIENCE_FACT"
    authority_level: Optional[int] = 95
    limit: Optional[int] = 3
    language: Optional[str] = "zh-CN"
    publisher: Optional[str] = "谷歌学术"


class FactEvidenceItem(BaseModel):
    evidence_id: str
    source_name: str
    source_url: Optional[str] = None
    publisher: Optional[str] = None
    authority_level: int
    score: float
    snippet: str


class LiteratureReviewRequest(BaseModel):
    story_id: int
    title: str
    content: str
    target_audience: Optional[str] = None
    age_group: Optional[str] = None


class LiteratureReviewResponse(BaseModel):
    passed: bool
    feedback: str
    revised_content: str

# --------------- Reader Schemas ---------------
class ReaderRequest(BaseModel):
    story_id: int
    title: Optional[str] = None
    content: str
    age_group: Optional[str] = None
    target_audience: Optional[str] = None


class ReaderRefineRequest(BaseModel):
    story_id: int
    title: Optional[str] = None
    content: str
    feedback: str
    age_group: Optional[str] = None
    target_audience: Optional[str] = None

class ReaderResponse(BaseModel):
    score: int
    feedback: str


class ReaderRefineResponse(BaseModel):
    revised_content: str
    optimization_notes: Optional[str] = None
    version: str = "4.0"

# --------------- Illustrator Schemas ---------------
class IllustratorRequest(BaseModel):
    story_id: int
    content: str
    image_count: Optional[int] = 4
    art_style: Optional[str] = "卡通"
    extra_requirements: Optional[str] = ""


class IllustratorRegenerateRequest(BaseModel):
    story_id: int
    scene_id: int
    image_prompt: str
    feedback: str
    art_style: Optional[str] = "卡通"
    extra_requirements: Optional[str] = ""
    
class IllustratorResponse(BaseModel):
    scenes: List[Dict[str, str]]


# --------------- Illustration Review Schemas ---------------
class IllustrationSceneItem(BaseModel):
    scene_id: int
    image_url: Optional[str] = None
    summary: Optional[str] = None
    image_prompt: Optional[str] = None
    text_chunk: Optional[str] = None


class CharacterDescription(BaseModel):
    gender: Optional[str] = None
    ageRange: Optional[str] = None
    hairStyle: Optional[str] = None
    clothing: Optional[str] = None
    features: Optional[List[str]] = None


class CharacterConfig(BaseModel):
    referenceImage: Optional[str] = None
    description: Optional[CharacterDescription] = None
    consistencyLevel: Optional[str] = None


class CharacterSummary(BaseModel):
    appearance: Optional[str] = None
    clothing: Optional[str] = None
    style: Optional[str] = None


class CharacterConsistencyIssue(BaseModel):
    type: Optional[str] = None
    description: Optional[str] = None
    scene_ids: Optional[List[int]] = None


class IllogicalIssueItem(BaseModel):
    category: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    suggestion: Optional[str] = None


class IllogicalSceneCheck(BaseModel):
    has_illogical_issues: Optional[bool] = None
    issues: Optional[List[IllogicalIssueItem]] = None
    overall_assessment: Optional[str] = None
    fix_priority: Optional[List[str]] = None


class CharacterConsistency(BaseModel):
    status: Optional[str] = None
    score: Optional[int] = None
    issues: Optional[List[CharacterConsistencyIssue]] = None
    character_summary: Optional[CharacterSummary] = None
    suggestion: Optional[str] = None
    priority_fixes: Optional[List[str]] = None


class SceneReview(BaseModel):
    scene_id: int
    science_status: Optional[str] = None
    science_reason: Optional[str] = None
    science_suggestion: Optional[str] = None
    logic_issues: Optional[List[str]] = None
    visual_suggestions: Optional[str] = None
    illogical_check: Optional[IllogicalSceneCheck] = None
    character_consistency: Optional[CharacterConsistency] = None


class OverallSummary(BaseModel):
    science_pass_rate: Optional[float] = None
    character_consistency_score: Optional[int] = None
    total_scenes: Optional[int] = None
    passed_science: Optional[int] = None
    needs_fix_science: Optional[int] = None
    warning_science: Optional[int] = None


class ComprehensiveReview(BaseModel):
    final_status: Optional[str] = None
    overall_score: Optional[int] = None
    science_score: Optional[int] = None
    consistency_score: Optional[int] = None
    logic_score: Optional[int] = None
    summary: Optional[str] = None
    required_fixes: Optional[List[str]] = None
    optional_improvements: Optional[List[str]] = None
    estimated_rework_effort: Optional[str] = None


class IllustrationReviewResponse(BaseModel):
    reviews: List[SceneReview]
    overall_summary: OverallSummary
    character_consistency_overall: Optional[CharacterConsistency] = None
    comprehensive_review: Optional[ComprehensiveReview] = None


class IllustrationReviewRequest(BaseModel):
    story_id: Optional[int] = None
    scenes: List[IllustrationSceneItem]
    character_config: Optional[CharacterConfig] = None


# --------------- Publisher Schemas ---------------
class PublisherRequest(BaseModel):
    story_id: Optional[int] = None
    title: str
    content: str
    glossary: Optional[List[Dict[str, str]]] = None
    illustrations: Optional[List[Dict[str, Any]]] = None
    highlight_terms: Optional[List[str]] = None
    layout_type: Optional[str] = "paragraph_image"


class PublisherExportResponse(BaseModel):
    filename: str
    download_url: str


# =============== Knowledge Base Schemas ===============

class KnowledgeDocumentBase(BaseModel):
    """知识库文档基础模型"""
    source_name: str = Field(..., description="来源名称，如'人教版小学科学三年级'")
    source_url: Optional[str] = Field(None, description="来源URL链接")
    publisher: Optional[str] = Field(None, description="出版社/发布方")
    author: Optional[str] = Field(None, description="作者")
    publish_year: Optional[int] = Field(None, description="出版年份")
    authority_level: int = Field(80, ge=0, le=100, description="权威度评分 0-100")
    doc_type: str = Field("SCIENCE_FACT", description="文档类型: SCIENCE_FACT(科学事实)/FACT(通用)")
    topic_tags: Optional[List[str]] = Field(None, description="主题标签，如['天文学', '物理学']")
    audience_tags: Optional[List[str]] = Field(None, description="受众标签，如['6-12岁', '小学']")
    style_tags: Optional[List[str]] = Field(None, description="风格标签，如['故事型', '探险型']")
    award_tags: Optional[List[str]] = Field(None, description="奖项标签，如['全国优秀科普作品奖']")
    content: str = Field(..., description="文档完整内容")


class KnowledgeDocumentCreate(KnowledgeDocumentBase):
    """创建知识库文档请求"""
    pass


class KnowledgeDocumentUpdate(BaseModel):
    """更新知识库文档请求"""
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    publisher: Optional[str] = None
    author: Optional[str] = None
    publish_year: Optional[int] = None
    authority_level: Optional[int] = Field(None, ge=0, le=100)
    doc_type: Optional[str] = None
    topic_tags: Optional[List[str]] = None
    audience_tags: Optional[List[str]] = None
    style_tags: Optional[List[str]] = None
    award_tags: Optional[List[str]] = None
    content: Optional[str] = None


class KnowledgeDocumentResponse(BaseModel):
    """知识库文档响应"""
    id: int
    source_name: str
    source_url: Optional[str] = None
    publisher: Optional[str] = None
    author: Optional[str] = None
    publish_year: Optional[int] = None
    authority_level: int
    doc_type: str
    topic_tags: Optional[List[str]] = None
    audience_tags: Optional[List[str]] = None
    style_tags: Optional[List[str]] = None
    award_tags: Optional[List[str]] = None
    content: str
    chunk_count: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KnowledgeDocumentListItem(BaseModel):
    """知识库文档列表项（简化版，不含大文本内容）"""
    id: int
    source_name: str
    source_url: Optional[str] = None
    publisher: Optional[str] = None
    author: Optional[str] = None
    publish_year: Optional[int] = None
    authority_level: int
    doc_type: str
    topic_tags: Optional[List[str]] = None
    audience_tags: Optional[List[str]] = None
    style_tags: Optional[List[str]] = None
    award_tags: Optional[List[str]] = None
    content_preview: Optional[str] = None
    chunk_count: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KnowledgeDocumentListResponse(BaseModel):
    """知识库文档列表响应"""
    items: List[KnowledgeDocumentListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class KnowledgeChunkResponse(BaseModel):
    """知识分块响应"""
    id: int
    document_id: int
    chunk_index: int
    chunk_text: str
    keywords: Optional[List[str]] = None
    score: Optional[float] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KnowledgeSearchRequest(BaseModel):
    """知识库检索请求"""
    query: str = Field(..., description="检索查询文本")
    top_k: int = Field(5, ge=1, le=20, description="返回结果数量")
    doc_type: Optional[str] = Field(None, description="文档类型筛选")
    topic_tag: Optional[str] = Field(None, description="主题标签筛选")
    audience_tag: Optional[str] = Field(None, description="受众标签筛选")
    min_authority_level: Optional[int] = Field(None, ge=0, le=100, description="最低权威度")


class KnowledgeSearchResponse(BaseModel):
    """知识库检索响应"""
    query: str
    results: List[Dict[str, Any]]
    total: int


class KnowledgeBatchImportRequest(BaseModel):
    """批量导入请求"""
    documents: List[KnowledgeDocumentCreate]
    auto_index: bool = Field(True, description="是否自动索引")


class KnowledgeBatchImportResponse(BaseModel):
    """批量导入响应"""
    success_count: int
    failed_count: int
    errors: Optional[List[Dict[str, Any]]] = None
    document_ids: Optional[List[int]] = None


class KnowledgeStatsResponse(BaseModel):
    """知识库统计信息"""
    total_documents: int
    total_chunks: int
    doc_type_counts: Dict[str, int]
    topic_tag_counts: Dict[str, int]
    audience_tag_counts: Dict[str, int]
    avg_authority_level: float
    recent_documents: List[KnowledgeDocumentListItem]


class KnowledgeReindexResponse(BaseModel):
    """重新索引响应"""
    document_id: int
    chunk_count: int
    status: str


# =============== Knowledge Collector Schemas ===============

class CollectFromSiteRequest(BaseModel):
    """从指定网站采集请求"""
    site_name: str = Field(..., description="网站名称: kepu_net_cn(中国科普博览)/sciencenet_cn(科学网)/guokr_com(果壳网)/kepu_gov_cn(科普中国)/cas_voice(中科院之声)")
    limit: int = Field(10, ge=1, le=50, description="采集数量")
    doc_type: str = Field("SCIENCE_FACT", description="入库文档类型")
    auto_ingest: bool = Field(True, description="是否自动入库")


class CollectAllSitesRequest(BaseModel):
    """从所有网站采集请求"""
    per_site_limit: int = Field(5, ge=1, le=20, description="每个网站采集数量")
    doc_type: str = Field("SCIENCE_FACT", description="入库文档类型")
    auto_ingest: bool = Field(True, description="是否自动入库")


class CollectedArticlePreview(BaseModel):
    """采集文章预览"""
    source_name: str
    source_url: str
    title: str
    author: Optional[str] = None
    publisher: Optional[str] = None
    publish_date: Optional[str] = None
    content_preview: Optional[str] = None
    topic_tags: Optional[List[str]] = None
    authority_level: int


class CollectFromSiteResponse(BaseModel):
    """网站采集响应"""
    site_name: str
    collected_count: int
    articles: List[CollectedArticlePreview]
    ingested_count: Optional[int] = None
    ingest_results: Optional[List[Dict[str, Any]]] = None


class CollectAllSitesResponse(BaseModel):
    """全部网站采集响应"""
    total_collected: int
    per_site_results: Dict[str, CollectFromSiteResponse]
    total_ingested: Optional[int] = None


class ListSitesResponse(BaseModel):
    """列出支持的网站"""
    sites: List[Dict[str, str]]


# =============== Topic Search Schemas ===============

class TopicSearchRequest(BaseModel):
    """按主题搜索请求"""
    topic: str = Field(..., description="搜索主题/关键词", min_length=2)
    sites: Optional[List[str]] = Field(None, description="指定搜索的网站列表，不指定则搜索所有支持的网站")
    limit_per_site: int = Field(3, ge=1, le=10, description="每个网站最多返回的文章数")
    doc_type: str = Field("SCIENCE_FACT", description="入库文档类型")
    auto_ingest: bool = Field(True, description="是否自动入库到知识库")


class TopicSearchResult(BaseModel):
    """主题搜索结果项"""
    source_name: str
    source_url: str
    title: str
    author: Optional[str] = None
    publisher: Optional[str] = None
    content_preview: Optional[str] = None
    topic_tags: Optional[List[str]] = None
    authority_level: int
    document_id: Optional[int] = None  # 如果已入库，则包含文档ID


class TopicSearchResponse(BaseModel):
    """主题搜索响应"""
    topic: str
    total_found: int
    results: List[TopicSearchResult]
    ingested_count: Optional[int] = None
    sites_searched: List[str]


# =============== 知识图谱 Schemas ===============

class KnowledgeGraphEntityBase(BaseModel):
    """知识图谱实体基础模型"""
    name: str = Field(..., description="实体名称", min_length=1, max_length=200)
    entity_type: str = Field(..., description="实体类型：CONCEPT/OBJECT/ORGANISM等")
    description: Optional[str] = Field(None, description="实体描述")
    aliases: Optional[List[str]] = Field(None, description="别名列表")
    properties: Optional[Dict[str, Any]] = Field(None, description="扩展属性")
    source_document_id: Optional[int] = Field(None, description="来源文档ID")
    confidence: float = Field(0.8, ge=0.0, le=1.0, description="置信度")


class KnowledgeGraphEntityCreate(KnowledgeGraphEntityBase):
    """创建实体请求"""
    pass


class KnowledgeGraphEntityUpdate(BaseModel):
    """更新实体请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    entity_type: Optional[str] = None
    description: Optional[str] = None
    aliases: Optional[List[str]] = None
    properties: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class KnowledgeGraphEntityResponse(BaseModel):
    """实体响应"""
    id: int
    name: str
    entity_type: str
    description: Optional[str] = None
    aliases: Optional[List[str]] = None
    properties: Optional[Dict[str, Any]] = None
    source_document_id: Optional[int] = None
    confidence: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KnowledgeGraphRelationBase(BaseModel):
    """知识图谱关系基础模型"""
    source_entity_id: int = Field(..., description="源实体ID")
    target_entity_id: int = Field(..., description="目标实体ID")
    relation_type: str = Field(..., description="关系类型：IS_A/PART_OF/CAUSES等")
    description: Optional[str] = Field(None, description="关系描述")
    properties: Optional[Dict[str, Any]] = Field(None, description="扩展属性")
    source_document_id: Optional[int] = Field(None, description="来源文档ID")
    confidence: float = Field(0.8, ge=0.0, le=1.0, description="置信度")


class KnowledgeGraphRelationCreate(KnowledgeGraphRelationBase):
    """创建关系请求"""
    pass


class KnowledgeGraphRelationUpdate(BaseModel):
    """更新关系请求"""
    relation_type: Optional[str] = None
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class KnowledgeGraphRelationResponse(BaseModel):
    """关系响应"""
    id: int
    source_entity_id: int
    target_entity_id: int
    relation_type: str
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    source_document_id: Optional[int] = None
    confidence: float
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KnowledgeGraphEntitySearchRequest(BaseModel):
    """实体搜索请求"""
    query: str = Field(..., description="搜索查询", min_length=1)
    entity_type: Optional[str] = Field(None, description="实体类型筛选")
    limit: int = Field(10, ge=1, le=50, description="返回结果数量")
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="最低置信度")


class KnowledgeGraphNeighborsRequest(BaseModel):
    """获取邻居请求"""
    entity_id: int = Field(..., description="实体ID")
    relation_type: Optional[str] = Field(None, description="关系类型筛选")
    max_depth: int = Field(2, ge=1, le=3, description="最大深度")
    limit: int = Field(50, ge=1, le=200, description="最大节点数")


class KnowledgeGraphSubgraphResponse(BaseModel):
    """子图响应（用于可视化）"""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class KnowledgeGraphPathRequest(BaseModel):
    """路径查找请求"""
    source_entity_id: int = Field(..., description="源实体ID")
    target_entity_id: int = Field(..., description="目标实体ID")
    max_depth: int = Field(3, ge=1, le=5, description="最大路径深度")


class KnowledgeGraphPathResponse(BaseModel):
    """路径查找响应"""
    found: bool
    path: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None


class ExtractFromDocumentRequest(BaseModel):
    """从文档提取知识图谱请求"""
    document_id: int = Field(..., description="文档ID")
    auto_save: bool = Field(True, description="是否自动保存")


class ExtractFromTextRequest(BaseModel):
    """从自定义文本提取知识图谱请求"""
    text: str = Field(..., description="文本内容")
    auto_save: bool = Field(True, description="是否自动保存")


class ExtractFromTopicRequest(BaseModel):
    """按词条生成文本并提取知识图谱请求"""
    topic: str = Field(..., description="主题词条，如“太阳”")
    auto_save: bool = Field(True, description="是否自动保存")


class ExtractFromWikipediaRequest(BaseModel):
    """从维基百科提取知识图谱请求"""
    title: str = Field(..., description="维基百科页面标题")
    language: str = Field("zh", description="语言")
    auto_save: bool = Field(True, description="是否自动保存")
    doc_type: str = Field("SCIENCE_FACT", description="文档类型")


class KnowledgeGraphExtractResponse(BaseModel):
    """知识图谱提取响应"""
    entities: List[KnowledgeGraphEntityResponse]
    relations: List[KnowledgeGraphRelationResponse]
    saved: bool
    message: str


class KnowledgeGraphStatsResponse(BaseModel):
    """知识图谱统计响应"""
    total_entities: int
    total_relations: int
    entity_type_counts: Dict[str, int]
    relation_type_counts: Dict[str, int]
    avg_confidence: float
    recent_entities: List[KnowledgeGraphEntityResponse]
