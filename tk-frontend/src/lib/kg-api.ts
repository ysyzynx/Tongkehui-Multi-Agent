/**
 * 知识图谱API客户端
 */
import { fetchApi } from './api';

interface ApiEnvelope<T> {
  code: number;
  msg: string;
  data: T;
}

async function requestKGData<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetchApi(path, init);
  const payload = (await resp.json()) as Partial<ApiEnvelope<T>>;

  if (typeof payload.code === 'number' && payload.code !== 200) {
    throw new Error(payload.msg || '知识图谱请求失败');
  }

  if (!('data' in payload)) {
    throw new Error(payload.msg || '知识图谱接口返回格式异常');
  }

  return payload.data as T;
}

export type EntityType =
  | 'CONCEPT'
  | 'OBJECT'
  | 'ORGANISM'
  | 'PERSON'
  | 'PLANET'
  | 'PHENOMENON'
  | 'PROCESS'
  | 'DEVICE'
  | 'PLACE'
  | 'EVENT';

export type RelationType =
  | 'IS_A'
  | 'PART_OF'
  | 'HAS_PART'
  | 'CAUSES'
  | 'IS_CAUSED_BY'
  | 'RELATED_TO'
  | 'INTERACTS_WITH'
  | 'LIVES_IN'
  | 'DISCOVERED_BY'
  | 'EXAMPLE_OF'
  | 'SIMILAR_TO'
  | 'CONTRASTS_WITH';

export interface KnowledgeGraphEntity {
  id: number;
  name: string;
  entity_type: EntityType;
  description?: string;
  aliases?: string[];
  properties?: Record<string, any>;
  source_document_id?: number;
  confidence: number;
  created_at?: string;
  updated_at?: string;
}

export interface KnowledgeGraphRelation {
  id: number;
  source_entity_id: number;
  target_entity_id: number;
  relation_type: RelationType;
  description?: string;
  properties?: Record<string, any>;
  source_document_id?: number;
  confidence: number;
  created_at?: string;
}

export interface EntityTypeConfig {
  [key: string]: string;
}

export interface RelationTypeConfig {
  [key: string]: string;
}

export interface KGStats {
  total_entities: number;
  total_relations: number;
  entity_type_counts: Record<string, number>;
  relation_type_counts: Record<string, number>;
  avg_confidence: number;
  recent_entities: KnowledgeGraphEntity[];
}

export interface SubgraphData {
  nodes: KnowledgeGraphEntity[];
  edges: KnowledgeGraphRelation[];
}

export interface EntityListResult {
  results: KnowledgeGraphEntity[];
  total: number;
}

export interface PathData {
  found: boolean;
  path?: KnowledgeGraphEntity[];
  edges?: KnowledgeGraphRelation[];
}

// 实体颜色映射
export const ENTITY_COLORS: Record<EntityType, string> = {
  CONCEPT: '#FF6B6B',
  OBJECT: '#4ECDC4',
  ORGANISM: '#45B7D1',
  PERSON: '#96CEB4',
  PLANET: '#FFEAA7',
  PHENOMENON: '#DDA0DD',
  PROCESS: '#98D8C8',
  DEVICE: '#F7DC6F',
  PLACE: '#BB8FCE',
  EVENT: '#85C1E9',
};

// 实体类型中文映射
export const ENTITY_TYPE_ZH: Record<string, string> = {
  CONCEPT: '概念',
  OBJECT: '物体',
  ORGANISM: '生物',
  PERSON: '人物',
  PLANET: '天体/星球',
  PHENOMENON: '现象',
  PROCESS: '过程',
  DEVICE: '设备',
  PLACE: '地点',
  EVENT: '事件',
};

// 关系颜色映射
export const RELATION_COLORS: Record<RelationType, string> = {
  IS_A: '#2ECC71',
  PART_OF: '#3498DB',
  HAS_PART: '#9B59B6',
  CAUSES: '#E74C3C',
  IS_CAUSED_BY: '#E67E22',
  RELATED_TO: '#95A5A6',
  INTERACTS_WITH: '#1ABC9C',
  LIVES_IN: '#27AE60',
  DISCOVERED_BY: '#8E44AD',
  EXAMPLE_OF: '#F39C12',
  SIMILAR_TO: '#16A085',
  CONTRASTS_WITH: '#C0392B',
};

/**
 * 获取实体类型和关系类型定义
 */
export async function getTypeDefinitions(): Promise<{
  entity_types: EntityTypeConfig;
  relation_types: RelationTypeConfig;
}> {
  return requestKGData('/api/kg/types');
}

/**
 * 获取知识图谱统计
 */
export async function getKGStats(): Promise<KGStats> {
  return requestKGData('/api/kg/stats');
}

/**
 * 删除指定的单个实体及其所有关联边
 */
export async function deleteEntity(entityId: number): Promise<{ success: boolean; msg?: string }> {
  return requestKGData(`/api/kg/entities/${entityId}`, { method: 'DELETE' });
}

/**
 * 清空整个知识图谱
 */
export async function clearKnowledgeGraph(): Promise<{ success: boolean; msg?: string }> {
  return requestKGData('/api/kg/clear?confirm=true', { method: 'DELETE' });
}

/**
 * 搜索实体
 */
export async function searchEntities(
  query: string,
  entity_type?: EntityType,
  limit = 10,
  min_confidence?: number
): Promise<KnowledgeGraphEntity[]> {
  const result = await requestKGData<{ results: KnowledgeGraphEntity[] }>('/api/kg/entities/search', {
    method: 'POST',
    body: JSON.stringify({
      query,
      entity_type,
      limit,
      min_confidence,
    }),
  });
  return result.results;
}

/**
 * 分页获取实体列表（用于管理页）
 */
export async function listEntities(options?: {
  limit?: number;
  offset?: number;
  entity_type?: EntityType;
  keyword?: string;
}): Promise<EntityListResult> {
  const limit = options?.limit ?? 30;
  const offset = options?.offset ?? 0;

  // 有关键词时复用搜索接口，避免依赖后端分页实现差异。
  if (options?.keyword && options.keyword.trim()) {
    const results = await searchEntities(options.keyword.trim(), options.entity_type, limit);
    return { results, total: results.length };
  }

  const page = Math.floor(offset / Math.max(1, limit)) + 1;

  const params = new URLSearchParams();
  params.set('page', String(page));
  params.set('page_size', String(limit));
  if (options?.entity_type) params.set('entity_type', options.entity_type);
  if (options?.keyword && options.keyword.trim()) params.set('search', options.keyword.trim());

  const raw = await requestKGData<any>(`/api/kg/entities?${params}`);
  if (Array.isArray(raw)) {
    return { results: raw as KnowledgeGraphEntity[], total: raw.length };
  }

  const items = Array.isArray(raw?.items) ? (raw.items as KnowledgeGraphEntity[]) : [];
  const results = Array.isArray(raw?.results)
    ? (raw.results as KnowledgeGraphEntity[])
    : items.length > 0
    ? items
    : Array.isArray(raw?.entities)
    ? (raw.entities as KnowledgeGraphEntity[])
    : [];
  const total = typeof raw?.total === 'number' ? raw.total : results.length;
  return { results, total };
}

/**
 * 获取实体详情
 */
export async function getEntity(entityId: number): Promise<KnowledgeGraphEntity> {
  return requestKGData(`/api/kg/entities/${entityId}`);
}

/**
 * 获取实体的邻居节点
 */
export async function getEntityNeighbors(
  entityId: number,
  relation_type?: RelationType,
  max_depth = 2,
  limit = 50
): Promise<SubgraphData> {
  const params = new URLSearchParams();
  if (relation_type) params.set('relation_type', relation_type);
  params.set('max_depth', String(max_depth));
  params.set('limit', String(limit));

  return requestKGData(`/api/kg/entities/${entityId}/neighbors?${params}`);
}

/**
 * 获取子图
 */
export async function getSubgraph(
  topic?: string,
  entity_ids?: number[],
  max_nodes = 100
): Promise<SubgraphData> {
  const params = new URLSearchParams();
  if (topic) params.set('topic', topic);
  if (entity_ids?.length) params.set('entity_ids', entity_ids.join(','));
  params.set('max_nodes', String(max_nodes));

  return requestKGData(`/api/kg/subgraph?${params}`);
}

/**
 * 查找两个实体之间的路径
 */
export async function findPath(
  sourceEntityId: number,
  targetEntityId: number,
  max_depth = 3
): Promise<PathData> {
  const params = new URLSearchParams();
  params.set('source_entity_id', String(sourceEntityId));
  params.set('target_entity_id', String(targetEntityId));
  params.set('max_depth', String(max_depth));

  return requestKGData(`/api/kg/path?${params}`);
}

/**
 * 获取核心实体
 */
export async function getCentralEntities(top_k = 10): Promise<KnowledgeGraphEntity[]> {
  const params = new URLSearchParams();
  params.set('top_k', String(top_k));

  const result = await requestKGData<{ entities: KnowledgeGraphEntity[] }>(
    `/api/kg/central-entities?${params}`
  );
  return result.entities;
}

/**
 * 获取社区
 */
export async function getCommunities(): Promise<any[]> {
  const result = await requestKGData<{ communities: any[] }>('/api/kg/communities');
  return result.communities;
}

/**
 * 创建实体
 */
export async function createEntity(
  entity: Omit<KnowledgeGraphEntity, 'id' | 'created_at' | 'updated_at'>
): Promise<KnowledgeGraphEntity> {
  return requestKGData('/api/kg/entities', {
    method: 'POST',
    body: JSON.stringify(entity),
  });
}

/**
 * 更新实体
 */
export async function updateEntity(
  entityId: number,
  updates: Partial<Omit<KnowledgeGraphEntity, 'id' | 'created_at' | 'updated_at'>>
): Promise<KnowledgeGraphEntity> {
  return requestKGData(`/api/kg/entities/${entityId}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
}

/**
 * 创建关系
 */
export async function createRelation(
  relation: Omit<KnowledgeGraphRelation, 'id' | 'created_at'>
): Promise<KnowledgeGraphRelation> {
  return requestKGData('/api/kg/relations', {
    method: 'POST',
    body: JSON.stringify(relation),
  });
}

/**
 * 从文档提取知识图谱
 */
export async function extractFromDocument(
  documentId: number,
  autoSave = true
): Promise<{
  entities: KnowledgeGraphEntity[];
  relations: KnowledgeGraphRelation[];
  saved: boolean;
  message: string;
}> {
  return requestKGData('/api/kg/extract-from-document', {
    method: 'POST',
    body: JSON.stringify({
      document_id: documentId,
      auto_save: autoSave,
    }),
  });
}

/**
 * 从维基百科提取知识图谱
 */
export async function extractFromWikipedia(
  title: string,
  language = 'zh',
  autoSave = true,
  doc_type = 'SCIENCE_FACT'
): Promise<{
  entities: KnowledgeGraphEntity[];
  relations: KnowledgeGraphRelation[];
  document_info: any;
  saved: boolean;
  message: string;
}> {
  return requestKGData('/api/kg/extract-from-wikipedia', {
    method: 'POST',
    body: JSON.stringify({
      title,
      language,
      auto_save: autoSave,
      doc_type,
    }),
  });
}

/**
 * 从纯文本提取知识图谱
 */
export async function extractFromText(
  text: string,
  autoSave = true
): Promise<{
  entities: KnowledgeGraphEntity[];
  relations: KnowledgeGraphRelation[];
  saved: boolean;
  message: string;
}> {
  return requestKGData('/api/kg/extract-from-text', {
    method: 'POST',
    body: JSON.stringify({
      text,
      auto_save: autoSave,
    }),
  });
}

/**
 * 从词条自动生成文本并提取知识图谱
 */
export async function extractFromTopic(
  topic: string,
  autoSave = true
): Promise<{
  entities: KnowledgeGraphEntity[];
  relations: KnowledgeGraphRelation[];
  saved: boolean;
  generated_text: string;
  message: string;
}> {
  return requestKGData('/api/kg/extract-from-topic', {
    method: 'POST',
    body: JSON.stringify({
      topic,
      auto_save: autoSave,
    }),
  });
}
