/**
 * 童科绘 API 客户端
 * 统一的前后端接口定义
 */

import { forceClearSession, getAuthToken } from './auth';

// ============== 基础配置 ==============

const getApiBaseUrl = (): string => {
  const envBase = import.meta.env.VITE_API_BASE_URL;
  if (envBase && envBase.trim()) {
    const normalized = envBase.trim();
    if (normalized.toLowerCase() === 'auto') {
      return window.location.origin;
    }
    return normalized;
  }
  if (import.meta.env.DEV) {
    return window.location.origin;
  }
  return window.location.origin;
};

export const API_BASE = getApiBaseUrl();

// ============== 通用响应类型 ==============

export interface ApiResponse<T = any> {
  code: number;
  msg: string;
  data: T;
  error?: string;
  traceback?: string;
}

// ============== 类型定义 ==============

// 创作相关
export interface StorySuggestion {
  title: string;
  category: string;
  clue: string;
}

export interface RagReference {
  id: number;
  source_name: string;
  source_url: string | null;
  publisher: string | null;
  author: string | null;
  publish_year: number | null;
  authority_level: number;
  doc_type: string;
  topic_tags: string[];
  snippet: string;
  score: number;
  selected: boolean;
}

export interface StoryData {
  id?: number;
  title: string;
  content: string;
  glossary: Array<{ term: string; explanation: string }>;
  rag_enabled: boolean;
  llm_provider?: string;
  llm_provider_label?: string;
  rag_evidence_used?: RagReference[];
  persist_warning?: string;
}

export interface CreateStoryParams {
  project_title?: string;
  theme: string;
  style?: string;
  age_group: string;
  target_audience: string;
  extra_requirements?: string;
  word_count: number;
  use_rag?: boolean;
  use_fact_rag?: boolean;
  use_deepsearch?: boolean;
  deepsearch_top_k?: number;
  rag_doc_type?: string;
  rag_top_k?: number;
  selected_rag_ids?: number[];
}

export interface SuggestTitlesParams {
  theme: string;
  target_audience?: string;
  age_group?: string;
}

export interface LLMProviderOption {
  provider: 'qwen' | 'volcengine' | 'hunyuan' | 'deepseek' | 'wenxin';
  label: string;
  base_url: string;
  default_model: string;
  default_vision_model: string;
}

export interface LLMRuntimeConfig {
  provider: string;
  provider_label: string;
  base_url: string;
  model: string;
  vision_model: string;
  has_api_key: boolean;
  api_key_masked: string;
  text?: {
    provider: string;
    provider_label: string;
    base_url: string;
    model: string;
    vision_model: string;
    has_api_key: boolean;
    api_key_masked: string;
  };
  image?: {
    provider: string;
    provider_label: string;
    has_api_key: boolean;
    api_key_masked: string;
  };
  image_provider_options?: Array<{ provider: 'volcengine' | 'qwen'; label: string }>;
}

export interface UpdateLLMConfigParams {
  provider?: 'qwen' | 'volcengine' | 'hunyuan' | 'deepseek' | 'wenxin';
  api_key?: string;
  text_provider?: 'qwen' | 'volcengine' | 'hunyuan' | 'deepseek' | 'wenxin';
  text_api_key?: string;
  image_provider?: 'volcengine' | 'qwen';
  image_api_key?: string;
}

// 审核相关
export interface ScienceCheckResult {
  passed: boolean;
  issues?: string[];
  modifications_made?: string[];
  suggestions: string;
  review_sections?: Array<{ [key: string]: any }>;
  highlight_terms?: string[];
  revised_content?: string;
  glossary?: Array<{ term: string; explanation: string }>;
  revised_glossary?: Array<{ term: string; explanation: string }>;
  evidence_used?: RagReference[];
  deepsearch_analysis?: { [key: string]: any };
  _debug?: { [key: string]: any };
  _iteration_history?: any[];
}

export interface LiteratureReviewResult {
  passed: boolean;
  feedback: string;
  revised_content: string;
}

export interface ReaderEvaluationResult {
  score: number;
  reader_feedback: string;
  [key: string]: any;
}

export interface ReaderRefineParams {
  story_id: number;
  title?: string;
  content: string;
  feedback: string;
  age_group?: string;
  target_audience?: string;
}

export interface ReaderRefineResult {
  revised_content: string;
  optimization_notes?: string;
  version?: string;
}

export interface CheckParams {
  story_id: number;
  title?: string;
  content: string;
  target_audience?: string;
  use_fact_rag?: boolean;
  evidence_top_k?: number;
  rag_doc_type?: string;
  use_deepsearch?: boolean;
  deepsearch_top_k?: number;
}

export interface LiteratureReviewParams {
  story_id: number;
  title: string;
  content: string;
  target_audience?: string;
  age_group?: string;
}

export interface ReaderEvaluateParams {
  story_id: number;
  title?: string;
  content: string;
  age_group?: string;
  target_audience?: string;
}

// 插画相关
export interface IllustrationScene {
  scene_id?: number;
  image_url?: string;
  summary?: string;
  image_prompt?: string;
  text_chunk?: string;
  [key: string]: any;
}

export interface IllustrationSuggestion {
  scenes: IllustrationScene[];
}

export interface IllustrationParams {
  story_id: number;
  content: string;
  image_count?: number;
  art_style?: string;
  extra_requirements?: string;
}

export interface RegenerateIllustrationParams {
  story_id: number;
  scene_id: number;
  image_prompt: string;
  feedback: string;
  art_style?: string;
  extra_requirements?: string;
}

// 知识库相关
export interface KnowledgeDocument {
  id: number;
  source_name: string;
  source_url?: string;
  publisher?: string;
  author?: string;
  publish_year?: number;
  authority_level: number;
  doc_type: string;
  topic_tags?: string[];
  audience_tags?: string[];
  style_tags?: string[];
  award_tags?: string[];
  content: string;
  chunk_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface KnowledgeDocumentListItem {
  id: number;
  source_name: string;
  source_url?: string;
  publisher?: string;
  author?: string;
  publish_year?: number;
  authority_level: number;
  doc_type: string;
  topic_tags?: string[];
  audience_tags?: string[];
  style_tags?: string[];
  award_tags?: string[];
  content_preview?: string;
  chunk_count?: number;
  created_at?: string;
}

export interface KnowledgeDocumentList {
  items: KnowledgeDocumentListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface KnowledgeSearchParams {
  query: string;
  top_k?: number;
  doc_type?: string;
  topic_tag?: string;
  audience_tag?: string;
  min_authority_level?: number;
}

export interface KnowledgeSearchResult {
  query: string;
  results: RagReference[];
  total: number;
}

export interface TopicSearchParams {
  topic: string;
  sites?: string[];
  limit_per_site?: number;
  doc_type?: string;
  auto_ingest?: boolean;
}

export interface TopicSearchResultItem {
  source_name: string;
  source_url: string;
  title: string;
  author?: string;
  publisher?: string;
  content_preview?: string;
  topic_tags?: string[];
  authority_level: number;
  document_id?: number;
  selected: boolean;
}

export interface TopicSearchResult {
  topic: string;
  total_found: number;
  results: TopicSearchResultItem[];
  ingested_count?: number;
  sites_searched: string[];
}

export interface KnowledgeStatsResult {
  total_documents: number;
  total_chunks: number;
  doc_type_counts: Record<string, number>;
  topic_tag_counts: Record<string, number>;
  audience_tag_counts: Record<string, number>;
  avg_authority_level: number;
  recent_documents: KnowledgeDocumentListItem[];
}

export interface CreateDocumentParams {
  source_name: string;
  source_url?: string;
  publisher?: string;
  author?: string;
  publish_year?: number;
  authority_level?: number;
  doc_type?: string;
  topic_tags?: string[];
  audience_tags?: string[];
  style_tags?: string[];
  award_tags?: string[];
  content: string;
}

// 发布相关
export interface IllustrationSceneForPublish {
  image_url?: string;
  summary?: string;
  image_prompt?: string;
  [key: string]: any;
}

export interface ExportPdfParams {
  story_id?: number;
  title: string;
  content: string;
  glossary?: Array<{ term: string; explanation: string }>;
  illustrations?: IllustrationSceneForPublish[];
  highlight_terms?: string[];
  layout_type?: string;
}

export interface ExportPdfResult {
  filename: string;
  download_url: string;
}

// ============== API 客户端类 ==============

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private joinUrl(path: string): string {
    if (!path) return this.baseUrl;
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path;
    }
    const base = this.baseUrl.endsWith('/') ? this.baseUrl.slice(0, -1) : this.baseUrl;
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    return `${base}${normalizedPath}`;
  }

  private async request<T>(
    path: string,
    init?: RequestInit
  ): Promise<ApiResponse<T>> {
    const url = this.joinUrl(path);

    const token = getAuthToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(init?.headers as Record<string, string>),
    };
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    try {
      console.log(`[API] 请求: ${url}`, init);
      const response = await fetch(url, {
        ...init,
        headers,
      });

      console.log(`[API] 响应状态: ${response.status} ${response.statusText}`);

      if (!response.ok) {
        if (response.status === 401) {
          forceClearSession();
          throw new Error('登录状态已失效，请重新登录');
        }

        // 尝试解析错误响应
        let errorDetail = '';
        try {
          const errorData = await response.json();
          console.error('[API] 错误响应:', errorData);
          errorDetail = errorData.msg || errorData.error || `${response.status} ${response.statusText}`;
          if (errorData.traceback) {
            console.error('[API] 错误堆栈:', errorData.traceback);
          }
        } catch {
          errorDetail = `API 请求失败: ${response.status} ${response.statusText}`;
        }
        throw new Error(errorDetail);
      }

      const data = await response.json();
      console.log(`[API] 响应数据:`, data);
      return data;
    } catch (error) {
      if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
        throw new Error(
          `无法连接到后端服务器。请确认后端服务已启动 (${this.baseUrl || 'http://localhost:8000'})`
        );
      }
      throw error;
    }
  }

  // ============== 创作相关接口 ==============

  /**
   * 根据主题生成标题建议
   */
  async suggestTitles(params: SuggestTitlesParams): Promise<StorySuggestion[]> {
    const resp = await this.request<{ suggestions: StorySuggestion[] }>('/api/story/suggest-titles', {
      method: 'POST',
      body: JSON.stringify(params),
    });
    if (resp.code !== 200) {
      throw new Error(resp.msg || '获取标题建议失败');
    }
    return resp.data.suggestions;
  }

  /**
   * 创建故事
   */
  async createStory(params: CreateStoryParams): Promise<StoryData> {
    const resp = await this.request<StoryData>('/api/story/create', {
      method: 'POST',
      body: JSON.stringify(params),
    });
    if (resp.code !== 200) {
      throw new Error(resp.msg || '创建故事失败');
    }
    return resp.data;
  }

  // ============== LLM 配置接口 ==============

  async getLlmProviders(): Promise<LLMProviderOption[]> {
    const resp = await this.request<{ options: LLMProviderOption[] }>('/api/llm-config/options');
    if (resp.code !== 200) {
      throw new Error(resp.msg || '获取LLM供应商失败');
    }
    return resp.data.options;
  }

  async getCurrentLlmConfig(): Promise<LLMRuntimeConfig> {
    const resp = await this.request<LLMRuntimeConfig>('/api/llm-config/current');
    if (resp.code !== 200) {
      throw new Error(resp.msg || '获取当前LLM配置失败');
    }
    return resp.data;
  }

  async updateLlmConfig(params: UpdateLLMConfigParams): Promise<LLMRuntimeConfig> {
    const resp = await this.request<LLMRuntimeConfig>('/api/llm-config/update', {
      method: 'POST',
      body: JSON.stringify(params),
    });
    if (resp.code !== 200) {
      throw new Error(resp.msg || '更新LLM配置失败');
    }
    return resp.data;
  }

  // ============== 审核相关接口 ==============

  /**
   * 科学审核
   */
  async scienceCheck(params: CheckParams): Promise<ScienceCheckResult> {
    const resp = await this.request<ScienceCheckResult>('/api/check/verify', {
      method: 'POST',
      body: JSON.stringify(params),
    });
    if (resp.code !== 200) {
      throw new Error(resp.msg || '科学审核失败');
    }
    return resp.data;
  }

  /**
   * 自反馈科学审核
   */
  async scienceCheckSelfFeedback(params: CheckParams): Promise<ScienceCheckResult> {
    const resp = await this.request<ScienceCheckResult>('/api/check/verify-self-feedback', {
      method: 'POST',
      body: JSON.stringify(params),
    });
    if (resp.code !== 200) {
      throw new Error(resp.msg || '科学审核失败');
    }
    return resp.data;
  }

  /**
   * 文学审核
   */
  async literatureReview(params: LiteratureReviewParams): Promise<LiteratureReviewResult> {
    const resp = await this.request<LiteratureReviewResult>('/api/literature/review', {
      method: 'POST',
      body: JSON.stringify(params),
    });
    if (resp.code !== 200) {
      throw new Error(resp.msg || '文学审核失败');
    }
    return resp.data;
  }

  /**
   * 读者评估
   */
  async readerEvaluate(params: ReaderEvaluateParams): Promise<ReaderEvaluationResult> {
    const resp = await this.request<ReaderEvaluationResult>('/api/reader/evaluate', {
      method: 'POST',
      body: JSON.stringify(params),
    });
    if (resp.code !== 200) {
      throw new Error(resp.msg || '读者评估失败');
    }
    return resp.data;
  }

  /**
   * 基于观众反馈微调正文（4.0）
   */
  async readerRefine(params: ReaderRefineParams): Promise<ReaderRefineResult> {
    const resp = await this.request<ReaderRefineResult>('/api/reader/refine', {
      method: 'POST',
      body: JSON.stringify(params),
    });
    if (resp.code !== 200) {
      throw new Error(resp.msg || '观众反馈微调失败');
    }
    return resp.data;
  }

  // ============== 插画相关接口 ==============

  /**
   * 生成插画建议
   */
  async suggestIllustrations(params: IllustrationParams): Promise<IllustrationSuggestion> {
    const resp = await this.request<{ scenes: IllustrationScene[] }>('/api/illustrator/suggest', {
      method: 'POST',
      body: JSON.stringify(params),
    });
    if (resp.code !== 200) {
      throw new Error(resp.msg || '生成插画建议失败');
    }
    return { scenes: resp.data.scenes };
  }

  /**
   * 重新生成插画
   */
  async regenerateIllustration(params: RegenerateIllustrationParams): Promise<{
    scene_id: number;
    image_prompt: string;
    image_url: string;
  }> {
    const resp = await this.request<{
      scene_id: number;
      image_prompt: string;
      image_url: string;
    }>('/api/illustrator/regenerate', {
      method: 'POST',
      body: JSON.stringify(params),
    });
    if (resp.code !== 200) {
      throw new Error(resp.msg || '重新生成插画失败');
    }
    return resp.data;
  }

  // ============== 知识库相关接口 ==============

  /**
   * 获取知识库文档列表
   */
  async listDocuments(params?: {
    page?: number;
    page_size?: number;
    doc_type?: string;
    topic_tag?: string;
    audience_tag?: string;
    min_authority?: number;
    search?: string;
  }): Promise<KnowledgeDocumentList> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.page_size) searchParams.set('page_size', String(params.page_size));
    if (params?.doc_type) searchParams.set('doc_type', params.doc_type);
    if (params?.topic_tag) searchParams.set('topic_tag', params.topic_tag);
    if (params?.audience_tag) searchParams.set('audience_tag', params.audience_tag);
    if (params?.min_authority !== undefined) searchParams.set('min_authority', String(params.min_authority));
    if (params?.search) searchParams.set('search', params.search);

    const queryString = searchParams.toString();
    const path = queryString ? `/api/knowledge/documents?${queryString}` : '/api/knowledge/documents';

    const resp = await this.request<KnowledgeDocumentList>(path);
    if (resp.code !== 200) {
      throw new Error(resp.msg || '获取文档列表失败');
    }
    return resp.data;
  }

  /**
   * 获取单个文档详情
   */
  async getDocument(documentId: number): Promise<KnowledgeDocument> {
    const resp = await this.request<KnowledgeDocument>(`/api/knowledge/documents/${documentId}`);
    if (resp.code !== 200) {
      throw new Error(resp.msg || '获取文档详情失败');
    }
    return resp.data;
  }

  /**
   * 创建文档
   */
  async createDocument(params: CreateDocumentParams): Promise<KnowledgeDocument> {
    const resp = await this.request<KnowledgeDocument>('/api/knowledge/documents', {
      method: 'POST',
      body: JSON.stringify(params),
    });
    if (resp.code !== 200) {
      throw new Error(resp.msg || '创建文档失败');
    }
    return resp.data;
  }

  /**
   * 搜索知识库
   */
  async searchKnowledge(params: KnowledgeSearchParams): Promise<KnowledgeSearchResult> {
    const resp = await this.request<KnowledgeSearchResult>('/api/knowledge/search', {
      method: 'POST',
      body: JSON.stringify(params),
    });
    if (resp.code !== 200) {
      throw new Error(resp.msg || '搜索知识库失败');
    }
    return resp.data;
  }

  /**
   * RAG 预检索
   */
  async preretrieveKnowledge(params: KnowledgeSearchParams): Promise<KnowledgeSearchResult> {
    const resp = await this.request<KnowledgeSearchResult>('/api/knowledge/preretrieve', {
      method: 'POST',
      body: JSON.stringify(params),
    });
    if (resp.code !== 200) {
      throw new Error(resp.msg || '检索知识库失败');
    }
    return resp.data;
  }

  /**
   * 按主题搜索科普网站
   */
  async searchTopic(params: TopicSearchParams): Promise<TopicSearchResult> {
    const resp = await this.request<TopicSearchResult>('/api/knowledge/search-topic', {
      method: 'POST',
      body: JSON.stringify(params),
    });
    if (resp.code !== 200) {
      throw new Error(resp.msg || '搜索主题失败');
    }
    return resp.data;
  }

  /**
   * 获取知识库统计
   */
  async getKnowledgeStats(): Promise<KnowledgeStatsResult> {
    const resp = await this.request<KnowledgeStatsResult>('/api/knowledge/stats');
    if (resp.code !== 200) {
      throw new Error(resp.msg || '获取统计信息失败');
    }
    return resp.data;
  }

  // ============== 发布相关接口 ==============

  /**
   * 导出 PDF
   */
  async exportPdf(params: ExportPdfParams): Promise<ExportPdfResult> {
    const resp = await this.request<ExportPdfResult>('/api/publisher/export-pdf', {
      method: 'POST',
      body: JSON.stringify(params),
    });
    if (resp.code !== 200) {
      throw new Error(resp.msg || '导出 PDF 失败');
    }
    return resp.data;
  }

  /**
   * 获取 PDF 下载链接
   */
  getPdfDownloadUrl(filename: string): string {
    return this.joinUrl(`/api/publisher/download/${filename}`);
  }

  // ============== 健康检查 ==============

  /**
   * 健康检查
   */
  async healthCheck(): Promise<{ status: string }> {
    const resp = await this.request<{ status: string }>('/');
    if (resp.code !== 200) {
      throw new Error(resp.msg || '健康检查失败');
    }
    return resp.data;
  }
}

// 导出单例
export const apiClient = new ApiClient();

export default apiClient;
