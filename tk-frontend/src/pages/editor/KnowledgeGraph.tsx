import { useEffect, useMemo, useState, useRef } from 'react';
import { AlertTriangle, ArrowLeft, Loader2, Search, Sparkles, ZoomIn, ZoomOut, Maximize, Trash2 } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  ENTITY_COLORS,
  ENTITY_TYPE_ZH,
  RELATION_COLORS,
  type KnowledgeGraphEntity,
  type KnowledgeGraphRelation,
  extractFromText,
  getEntityNeighbors,
  getKGStats,
  searchEntities,
  clearKnowledgeGraph,
  deleteEntity,
} from '../../lib/kg-api';

type GraphData = {
  nodes: KnowledgeGraphEntity[];
  edges: KnowledgeGraphRelation[];
};

type NodePoint = {
  id: number;
  x: number;
  y: number;
  node: KnowledgeGraphEntity;
};

type EdgeCurveMeta = {
  laneIndex: number;
  laneTotal: number;
};

type XY = { x: number; y: number };

function pruneIsolatedNodes(
  nodes: KnowledgeGraphEntity[],
  edges: KnowledgeGraphRelation[],
): { nodes: KnowledgeGraphEntity[]; edges: KnowledgeGraphRelation[] } {
  const linkedNodeIds = new Set<number>();
  for (const edge of edges) {
    linkedNodeIds.add(edge.source_entity_id);
    linkedNodeIds.add(edge.target_entity_id);
  }

  const nextNodes = nodes.filter((node) => linkedNodeIds.has(node.id));
  return { nodes: nextNodes, edges };
}

const GRAPH_WIDTH = 1120;
const GRAPH_HEIGHT = 680;

const RELATION_LABELS_ZH: Record<string, string> = {
  IS_A: '是一种',
  PART_OF: '是...的一部分',
  HAS_PART: '包含',
  CAUSES: '导致',
  IS_CAUSED_BY: '由...导致',
  RELATED_TO: '相关',
  INTERACTS_WITH: '相互作用',
  LIVES_IN: '生活在',
  DISCOVERED_BY: '由其发现',
  EXAMPLE_OF: '以此为例',
  SIMILAR_TO: '类似',
  CONTRASTS_WITH: '对比',
};

function relationLabelZh(relationType: string) {
  return RELATION_LABELS_ZH[relationType] || relationType;
}

function relationDisplayText(edge: KnowledgeGraphRelation) {
  const propsLabel = String(edge.properties?.relation_label || edge.properties?.relation_text || '').trim();
  if (propsLabel && propsLabel.length <= 10) return propsLabel;

  return relationLabelZh(edge.relation_type);
}

function clampConfidence(value: number | undefined) {
  if (typeof value !== 'number' || Number.isNaN(value)) return 0;
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}

function toNodePoints(
  nodes: KnowledgeGraphEntity[],
  edges: KnowledgeGraphRelation[],
  centerNodeId?: number | null,
): NodePoint[] {
  if (nodes.length === 0) return [];

  const centerX = GRAPH_WIDTH / 2;
  const centerY = GRAPH_HEIGHT / 2;
  const padding = 56;

  const indexById = new Map<number, number>();
  nodes.forEach((node, index) => indexById.set(node.id, index));

  const pos = new Array(nodes.length).fill(null).map((_, i) => {
    const angle = (Math.PI * 2 * i) / Math.max(1, nodes.length);
    const radius = Math.min(centerX, centerY) * 0.55;
    // 添加一点随机位移，破坏完美对称性，避免力导向陷入局部极小点（如节点停留在一条直线上）
    const jitterX = (Math.random() - 0.5) * 40;
    const jitterY = (Math.random() - 0.5) * 40;
    return {
      x: centerX + Math.cos(angle) * radius + jitterX,
      y: centerY + Math.sin(angle) * radius + jitterY,
    };
  });

  const velocity = new Array(nodes.length).fill(null).map(() => ({ x: 0, y: 0 }));

  const focusIndex = centerNodeId && indexById.has(centerNodeId) ? indexById.get(centerNodeId)! : -1;
  const iterations = 280; // 保持较充分迭代，同时避免过度发散
  const repulsion = 17000; // 提升疏散但不过度推离画布
  const spring = 0.04;
  const restLength = 195; // 稍增理想边长，降低拥挤
  const damping = 0.85;
  const gravity = 0.0012;

  for (let step = 0; step < iterations; step += 1) {
    // 节点间斥力
    for (let i = 0; i < nodes.length; i += 1) {
      for (let j = i + 1; j < nodes.length; j += 1) {
        const dx = pos[j].x - pos[i].x;
        const dy = pos[j].y - pos[i].y;
        const distSq = dx * dx + dy * dy + 1;
        const dist = Math.sqrt(distSq);
        const force = repulsion / distSq;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        velocity[i].x -= fx;
        velocity[i].y -= fy;
        velocity[j].x += fx;
        velocity[j].y += fy;
      }
    }

    // 边弹簧力
    for (const edge of edges) {
      const si = indexById.get(edge.source_entity_id);
      const ti = indexById.get(edge.target_entity_id);
      if (si === undefined || ti === undefined) continue;

      const dx = pos[ti].x - pos[si].x;
      const dy = pos[ti].y - pos[si].y;
      const dist = Math.max(1, Math.sqrt(dx * dx + dy * dy));
      const delta = dist - restLength;
      const force = delta * spring;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;

      velocity[si].x += fx;
      velocity[si].y += fy;
      velocity[ti].x -= fx;
      velocity[ti].y -= fy;
    }

    for (let i = 0; i < nodes.length; i += 1) {
      const locked = i === focusIndex;
      if (locked) {
        pos[i] = { x: centerX, y: centerY };
        velocity[i] = { x: 0, y: 0 };
        continue;
      }

      velocity[i].x += (centerX - pos[i].x) * gravity;
      velocity[i].y += (centerY - pos[i].y) * gravity;
      velocity[i].x *= damping;
      velocity[i].y *= damping;

      pos[i].x += velocity[i].x;
      pos[i].y += velocity[i].y;
      // 移除计算过程中的硬边界限制，允许图谱自由伸展，最后再经过整体等比例缩放到视口内
    }
  }

  // 有中心节点锁定时，若整体过于拥挤，则按中心做一次径向拉伸。
  if (focusIndex >= 0 && pos.length > 2) {
    let sumDist = 0;
    let count = 0;
    for (let i = 0; i < pos.length; i += 1) {
      if (i === focusIndex) continue;
      sumDist += Math.hypot(pos[i].x - centerX, pos[i].y - centerY);
      count += 1;
    }

    const avgDist = count > 0 ? sumDist / count : 0;
    const targetAvg = Math.min(centerX, centerY) * 0.62;
    if (avgDist > 1 && avgDist < targetAvg) {
      const scale = targetAvg / avgDist;
      for (let i = 0; i < pos.length; i += 1) {
        if (i === focusIndex) continue;
        pos[i].x = centerX + (pos[i].x - centerX) * scale;
        pos[i].y = centerY + (pos[i].y - centerY) * scale;
      }
    }
  }

  // 中心锁定模式下，将非中心节点限制在画布可视范围内，避免整图被推到视口外。
  if (focusIndex >= 0) {
    for (let i = 0; i < pos.length; i += 1) {
      if (i === focusIndex) {
        pos[i] = { x: centerX, y: centerY };
        continue;
      }
      pos[i].x = Math.min(GRAPH_WIDTH - padding, Math.max(padding, pos[i].x));
      pos[i].y = Math.min(GRAPH_HEIGHT - padding, Math.max(padding, pos[i].y));
    }
  }

  // 无中心锁定时，将布局结果拉伸到画布可用区域，尽可能铺满画布。
  if (focusIndex < 0 && pos.length > 1) {
    let minX = Number.POSITIVE_INFINITY;
    let maxX = Number.NEGATIVE_INFINITY;
    let minY = Number.POSITIVE_INFINITY;
    let maxY = Number.NEGATIVE_INFINITY;

    for (const p of pos) {
      minX = Math.min(minX, p.x);
      maxX = Math.max(maxX, p.x);
      minY = Math.min(minY, p.y);
      maxY = Math.max(maxY, p.y);
    }

    const srcW = Math.max(1, maxX - minX);
    const srcH = Math.max(1, maxY - minY);
    const dstW = GRAPH_WIDTH - padding * 2;
    const dstH = GRAPH_HEIGHT - padding * 2;

    // 采用等比例缩放，避免拉伸导致图谱变形（如水平挤压、垂直拉长等）
    const scale = Math.min(dstW / srcW, dstH / srcH) * 0.9; // 略微留余地 0.9
    const scaledW = srcW * scale;
    const scaledH = srcH * scale;

    // 居中偏移
    const offsetX = padding + (dstW - scaledW) / 2;
    const offsetY = padding + (dstH - scaledH) / 2;

    for (let i = 0; i < pos.length; i += 1) {
      pos[i].x = offsetX + (pos[i].x - minX) * scale;
      pos[i].y = offsetY + (pos[i].y - minY) * scale;
    }
  }

  return nodes.map((node, index) => ({
    id: node.id,
    x: pos[index].x,
    y: pos[index].y,
    node,
  }));
}

function buildEdgeCurveMeta(edges: KnowledgeGraphRelation[]): Map<number, EdgeCurveMeta> {
  const group = new Map<string, number[]>();
  edges.forEach((edge, idx) => {
    const a = Math.min(edge.source_entity_id, edge.target_entity_id);
    const b = Math.max(edge.source_entity_id, edge.target_entity_id);
    const key = `${a}-${b}`;
    const bucket = group.get(key) || [];
    bucket.push(idx);
    group.set(key, bucket);
  });

  const meta = new Map<number, EdgeCurveMeta>();
  group.forEach((indices) => {
    indices.forEach((edgeIndex, laneIndex) => {
      meta.set(edgeIndex, { laneIndex, laneTotal: indices.length });
    });
  });
  return meta;
}

function distancePointToSegment(point: XY, a: XY, b: XY): number {
  const abx = b.x - a.x;
  const aby = b.y - a.y;
  const apx = point.x - a.x;
  const apy = point.y - a.y;
  const abLenSq = abx * abx + aby * aby;

  if (abLenSq <= 1e-6) {
    const dx = point.x - a.x;
    const dy = point.y - a.y;
    return Math.sqrt(dx * dx + dy * dy);
  }

  const t = Math.max(0, Math.min(1, (apx * abx + apy * aby) / abLenSq));
  const cx = a.x + abx * t;
  const cy = a.y + aby * t;
  const dx = point.x - cx;
  const dy = point.y - cy;
  return Math.sqrt(dx * dx + dy * dy);
}

function clampToCanvas(point: XY, margin = 62): XY {
  return {
    x: Math.min(GRAPH_WIDTH - margin, Math.max(margin, point.x)),
    y: Math.min(GRAPH_HEIGHT - margin, Math.max(margin, point.y)),
  };
}

function suggestSparsePositionsForNewNodes(
  existingPoints: NodePoint[],
  existingEdges: KnowledgeGraphRelation[],
  mergedEdges: KnowledgeGraphRelation[],
  newNodeIds: number[],
  centerNodeId?: number | null,
): Record<number, XY> {
  if (newNodeIds.length === 0) return {};

  const posMap = new Map<number, XY>();
  for (const p of existingPoints) {
    posMap.set(p.id, { x: p.x, y: p.y });
  }

  const segments: Array<{ a: XY; b: XY }> = [];
  for (const edge of existingEdges) {
    const a = posMap.get(edge.source_entity_id);
    const b = posMap.get(edge.target_entity_id);
    if (a && b) segments.push({ a, b });
  }

  const fallbackCenter = centerNodeId && posMap.get(centerNodeId)
    ? posMap.get(centerNodeId)!
    : { x: GRAPH_WIDTH / 2, y: GRAPH_HEIGHT / 2 };

  const pickBestCandidate = (base: XY, seed: number) => {
    let best = clampToCanvas(base);
    let bestScore = Number.NEGATIVE_INFINITY;

    for (let ring = 0; ring < 4; ring += 1) {
      const radius = 150 + ring * 70;
      for (let step = 0; step < 12; step += 1) {
        const angle = (Math.PI * 2 * step) / 12 + seed * 0.41 + ring * 0.17;
        const candidate = clampToCanvas({
          x: base.x + Math.cos(angle) * radius,
          y: base.y + Math.sin(angle) * radius,
        });

        let minNodeDist = Number.POSITIVE_INFINITY;
        for (const p of posMap.values()) {
          const dx = candidate.x - p.x;
          const dy = candidate.y - p.y;
          const d = Math.sqrt(dx * dx + dy * dy);
          minNodeDist = Math.min(minNodeDist, d);
        }

        let minSegDist = Number.POSITIVE_INFINITY;
        for (const seg of segments) {
          minSegDist = Math.min(minSegDist, distancePointToSegment(candidate, seg.a, seg.b));
        }
        if (!Number.isFinite(minSegDist)) minSegDist = 140;

        const baseDist = Math.hypot(candidate.x - base.x, candidate.y - base.y);
        const score = Math.min(minNodeDist, minSegDist * 1.08) - baseDist * 0.12;

        if (score > bestScore) {
          bestScore = score;
          best = candidate;
        }
      }
    }

    return best;
  };

  const result: Record<number, XY> = {};

  newNodeIds.forEach((newNodeId, idx) => {
    const anchorPoints: XY[] = [];
    for (const edge of mergedEdges) {
      if (edge.source_entity_id === newNodeId) {
        const p = posMap.get(edge.target_entity_id);
        if (p) anchorPoints.push(p);
      } else if (edge.target_entity_id === newNodeId) {
        const p = posMap.get(edge.source_entity_id);
        if (p) anchorPoints.push(p);
      }
    }

    const base = anchorPoints.length > 0
      ? {
          x: anchorPoints.reduce((sum, p) => sum + p.x, 0) / anchorPoints.length,
          y: anchorPoints.reduce((sum, p) => sum + p.y, 0) / anchorPoints.length,
        }
      : fallbackCenter;

    const chosen = pickBestCandidate(base, idx + 1);
    result[newNodeId] = chosen;
    posMap.set(newNodeId, chosen);

    for (const edge of mergedEdges) {
      if (edge.source_entity_id === newNodeId || edge.target_entity_id === newNodeId) {
        const a = posMap.get(edge.source_entity_id);
        const b = posMap.get(edge.target_entity_id);
        if (a && b) segments.push({ a, b });
      }
    }
  });

  return result;
}

function formatConfidence(value: number | undefined) {
  return `${Math.round(clampConfidence(value) * 100)}%`;
}

function buildTopicSeedText(topic: string) {
  return [
    `主题：${topic}`,
    `${topic}是一个重要的科学主题。`,
    `请围绕${topic}说明其定义、组成部分、相关现象和作用机制。`,
    `请给出4到7个与${topic}高度相关的科学实体，并补充实体之间的关键关系，关系使用"是/属于/导致/包含/围绕/相互作用"等明确谓词。`,
    `内容要用于后续知识图谱抽取，因此实体名称应具体、可区分、避免泛词。`,
  ].join(' ');
}

export default function KnowledgeGraph() {
  const navigate = useNavigate();
  const location = useLocation();
  const returnTo =
    location.state && typeof location.state === 'object' && typeof (location.state as any).returnTo === 'string'
      ? (location.state as any).returnTo
      : '';
  const returnLabel =
    location.state && typeof location.state === 'object' && typeof (location.state as any).returnLabel === 'string'
      ? (location.state as any).returnLabel
      : '返回编辑页';
  const returnState =
    location.state && typeof location.state === 'object' && (location.state as any).returnState
      ? (location.state as any).returnState
      : undefined;
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] });
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [busyAction, setBusyAction] = useState('');
  const [error, setError] = useState('');
  const [actionTip, setActionTip] = useState('');

  const [stats, setStats] = useState<{ total_entities: number; total_relations: number } | null>(null);
  const [topicKeyword, setTopicKeyword] = useState('太阳系');
  const [textInput, setTextInput] = useState('');

  const [searchResults, setSearchResults] = useState<KnowledgeGraphEntity[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);
  const [centerNodeId, setCenterNodeId] = useState<number | null>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; nodeId: number } | null>(null);

  const svgRef = useRef<SVGSVGElement>(null);
  const [draggingNodeId, setDraggingNodeId] = useState<number | null>(null);
  const [draggedPositions, setDraggedPositions] = useState<Record<number, { x: number; y: number }>>({});
  // This ref keeps track of if the mouse was actually moved during mousedown
  const dragDidMove = useRef(false);

  // 画布平移与缩放状态
  const [viewBoxOffset, setViewBoxOffset] = useState({ x: 0, y: 0 });
  const [zoomScale, setZoomScale] = useState(1);
  const [isPanning, setIsPanning] = useState(false);
  const transformRef = useRef({ 
    isPanning: false,
    startX: 0, 
    startY: 0,
    currViewBoxX: 0,
    currViewBoxY: 0
  });

  function showError(message: string) {
    setError(message);
    setActionTip(message);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function showTip(message: string) {
    setActionTip(message);
  }

  const uniqueEdges = useMemo(() => {
    const seen = new Set<string>();
    const res: KnowledgeGraphRelation[] = [];
    for (const e of graphData.edges) {
      const label = relationDisplayText(e);
      const key = `${e.source_entity_id}-${e.target_entity_id}-${label}`;
      if (!seen.has(key)) {
        seen.add(key);
        res.push(e);
      }
    }
    return res;
  }, [graphData.edges]);

  const basePoints = useMemo(
    () => toNodePoints(graphData.nodes, uniqueEdges, centerNodeId),
    [graphData.nodes, uniqueEdges, centerNodeId],
  );

  const points = useMemo(() => {
    return basePoints.map((p) => {
      const override = draggedPositions[p.id];
      if (override) {
        return { ...p, x: override.x, y: override.y };
      }
      return p;
    });
  }, [basePoints, draggedPositions]);

  const edgeCurveMeta = useMemo(() => buildEdgeCurveMeta(uniqueEdges), [uniqueEdges]);

  const pointMap = useMemo(() => {
    const map = new Map<number, NodePoint>();
    for (const p of points) {
      map.set(p.id, p);
    }
    return map;
  }, [points]);

  const selectedNode = useMemo(
    () => graphData.nodes.find((item) => item.id === selectedNodeId) || null,
    [graphData.nodes, selectedNodeId],
  );

  const entityNameMap = useMemo(() => {
    const map = new Map<number, string>();
    graphData.nodes.forEach((node) => map.set(node.id, node.name));
    return map;
  }, [graphData.nodes]);

  const triples = useMemo(() => {
    return uniqueEdges.map((edge) => ({
      id: edge.id,
      source: entityNameMap.get(edge.source_entity_id) || `#${edge.source_entity_id}`,
      relation: relationDisplayText(edge),
      target: entityNameMap.get(edge.target_entity_id) || `#${edge.target_entity_id}`,
    }));
  }, [uniqueEdges, entityNameMap]);

  async function refreshStats() {
    try {
      const res = await getKGStats();
      setStats({ total_entities: res.total_entities, total_relations: res.total_relations });
    } catch {
      // 不阻断主流程
    }
  }

  async function handleClearGraph() {
    if (!window.confirm('此操作将清空数据库中的所有实体和连线（不可恢复！）。确定要清空吗？')) {
      return;
    }

    setBusyAction('clear');
    setError('');
    showTip('正在清空知识库...');
    try {
      await clearKnowledgeGraph();
      // 清空本地数据视图
      setGraphData({ nodes: [], edges: [] });
      setSearchResults([]);
      setSelectedNodeId(null);
      setCenterNodeId(null);
      await refreshStats();
      showTip('图谱数据库已完美清空！');
    } catch (e) {
      showError(e instanceof Error ? e.message : '清空数据库失败');
    } finally {
      setBusyAction('');
    }
  }

  function handleClearCanvas() {
    setGraphData({ nodes: [], edges: [] });
    setSelectedNodeId(null);
    setCenterNodeId(null);
    setDraggedPositions({});
    setActionTip('画布已清空，仅清除了当前视图内容。');
  }

  async function handleSearch() {
    const cleaned = topicKeyword.trim();
    if (!cleaned) return;

    setBusyAction('search');
    setLoadingGraph(true);
    setError('');
    showTip(`正在搜索"${cleaned}"...`);
    try {
      const localResult = await searchEntities(cleaned, undefined, 15);
      let mergedResults = [...localResult];
      let generatedCount = 0;

      // 本地命中不足时，自动补全到更可读的规模（目标 4-7 个实体）
      if (localResult.length < 4) {
        showTip(`本地仅命中 ${localResult.length} 个实体，正在调用 LLM 补全到 4-7 个相关实体...`);
        const topicSeedText = buildTopicSeedText(cleaned);
        const generated = await extractFromText(topicSeedText, true);
        const generatedEntities = generated.entities || [];
        generatedCount = generatedEntities.length;

        const map = new Map<number, KnowledgeGraphEntity>();
        [...localResult, ...generatedEntities].forEach((item) => {
          map.set(item.id, item);
        });
        mergedResults = Array.from(map.values());
        await refreshStats();
      }

      if (mergedResults.length === 0) {
        showError(`未找到"${cleaned}"相关实体，请尝试更具体词条。`);
        return;
      }

      // 搜索后只围绕一个主实体建图，避免把多个不相干命中混在同一画布。
      const lowered = cleaned.toLowerCase();
      const primary =
        mergedResults.find((item) => item.name.trim().toLowerCase() === lowered) ||
        mergedResults.find((item) => item.name.toLowerCase().includes(lowered)) ||
        mergedResults[0];

      const orderedResults = [primary, ...mergedResults.filter((item) => item.id !== primary.id)];
      setSearchResults(orderedResults.slice(0, 15));

      const localGraph = await getEntityNeighbors(primary.id, undefined, 2, 120);
      const graphNodes = localGraph.nodes || [];
      const graphEdges = localGraph.edges || [];

      if (graphNodes.length > 0) {
        setGraphData({ nodes: graphNodes, edges: graphEdges });
      } else {
        // 极端情况下邻居为空，也至少展示主实体本身。
        setGraphData({ nodes: [primary], edges: [] });
      }

      setSelectedNodeId(primary.id);
      setCenterNodeId(primary.id);

      if (generatedCount > 0) {
        showTip(`搜索完成：已围绕“${primary.name}”加载中心图谱；本地 ${localResult.length} 个，LLM 新增 ${generatedCount} 个候选。`);
      } else {
        showTip(`搜索完成：已围绕“${primary.name}”加载中心图谱。`);
      }
    } catch (e) {
      showError(e instanceof Error ? e.message : '搜索失败');
    } finally {
      setLoadingGraph(false);
      setBusyAction('');
    }
  }

  async function handleNodeExpand(entity: KnowledgeGraphEntity) {
    setBusyAction(`expand-${entity.id}`);
    setError('');
    showTip(`正在从本地扩展"${entity.name}"的邻居...`);
    try {
      let data = await getEntityNeighbors(entity.id, undefined, 2, 80);
      let newNodes = data.nodes || [];
      let newEdges = data.edges || [];

      // 判断本次查询是否能在当前画布上引入「新节点」
      const existingNodeIdsSet = new Set(graphData.nodes.map(n => n.id));
      const newToCanvasNodes = newNodes.filter(n => !existingNodeIdsSet.has(n.id) && n.id !== entity.id);

      // 如果本地获取的所有邻居都已经显示在画布上了（或者本地本来就没有邻居），则自动连线大模型深度挖掘。
      if (newToCanvasNodes.length === 0) {
        showTip(`"${entity.name}" 暂无更多未展示关联知识，正在连线大模型深入探索...`);
        const topicSeedText = buildTopicSeedText(entity.name);
        const generated = await extractFromText(topicSeedText, true);
        await refreshStats();
        // LLM抽取生成并存入数据库之后，再拉取一次邻居数据
        if (generated.entities && generated.entities.length > 0) {
          data = await getEntityNeighbors(entity.id, undefined, 2, 80);
          newNodes = data.nodes || [];
          newEdges = data.edges || [];
        }
      }

      const existingNodeIds = new Set(graphData.nodes.map((n) => n.id));
      const mergedNodes = [...graphData.nodes];
      newNodes.forEach((n) => {
        if (!existingNodeIds.has(n.id)) {
          mergedNodes.push(n);
        }
      });

      const existingEdgeIds = new Set(graphData.edges.map((e) => e.id));
      const mergedEdges = [...graphData.edges];
      newEdges.forEach((e) => {
        if (!existingEdgeIds.has(e.id)) {
          mergedEdges.push(e);
        }
      });

      const newNodeIds = mergedNodes
        .filter((n) => !existingNodeIds.has(n.id))
        .map((n) => n.id);

      const frozenExisting: Record<number, XY> = {};
      points.forEach((p) => {
        frozenExisting[p.id] = { x: p.x, y: p.y };
      });

      const sparseNew = suggestSparsePositionsForNewNodes(
        points,
        graphData.edges,
        mergedEdges,
        newNodeIds,
        entity.id,
      );

      setGraphData({ nodes: mergedNodes, edges: mergedEdges });
      setDraggedPositions({
        ...frozenExisting,
        ...sparseNew,
      });
      
      setSelectedNodeId(entity.id);
      if (newNodes.length > 1) {
        showTip(`扩展完成：成功并入相关节点与知识连线！`);
      } else {
        showTip(`探索完成：抱歉，未能寻找到关于"${entity.name}"的更多知识连线。`);
      }
    } catch (e) {
      showError(e instanceof Error ? e.message : '展开节点失败');
    } finally {
      setBusyAction('');
    }
  }

  async function handleExtractFromText() {
    const text = textInput.trim();
    if (text.length < 20) {
      showError('请输入至少 20 字文本，方便大模型抽取实体与关系');
      return;
    }

    setBusyAction('text');
    setError('');
    showTip('正在从自由文本抽取知识图谱，请稍候...');
    try {
      const data = await extractFromText(text, true);
      showTip(`文本抽取完成：${data.entities?.length || 0} 个实体，${data.relations?.length || 0} 条关系。`);
      await refreshStats();

      const nextNodes = data.entities || [];
      const nextEdges = data.relations || [];
      if (nextNodes.length > 0) {
        setGraphData({ nodes: nextNodes, edges: nextEdges });
        setSelectedNodeId(nextNodes[0]?.id ?? null);
        setCenterNodeId(null);
      } else {
        showError('抽取已完成，但未形成可用图谱节点，请尝试更长、更结构化的科普文本。');
      }
    } catch (e) {
      showError(e instanceof Error ? e.message : '文本抽取失败');
    } finally {
      setBusyAction('');
    }
  }

  async function handleDeleteNode(nodeId: number) {
    const node = graphData.nodes.find((n) => n.id === nodeId);
    if (!node) return;
    
    if (!window.confirm(`确定要从数据库彻底删除节点 "${node.name}" 及其相关的边吗？该操作不可恢复！`)) {
      return;
    }

    setContextMenu(null);
    setBusyAction('deleteNode');
    setError('');
    
    try {
      await deleteEntity(nodeId);

      // 记录删除前的屏幕坐标，删除后用于锁定剩余节点位置，避免整体重排跳动。
      const pointSnapshot = new Map<number, { x: number; y: number }>();
      points.forEach((p) => {
        pointSnapshot.set(p.id, { x: p.x, y: p.y });
      });

      // 本地乐观更新：剔除该节点和相关连线，并进一步清理孤立点。
      const nextEdges = graphData.edges.filter(
        (e) => e.source_entity_id !== nodeId && e.target_entity_id !== nodeId,
      );
      const nextNodes = graphData.nodes.filter((n) => n.id !== nodeId);
      const pruned = pruneIsolatedNodes(nextNodes, nextEdges);
      const remainNodeIds = new Set(pruned.nodes.map((n) => n.id));

      setGraphData(pruned);

      setSelectedNodeId((prev) => (prev !== null && remainNodeIds.has(prev) ? prev : null));
      setCenterNodeId((prev) => (prev !== null && remainNodeIds.has(prev) ? prev : null));

      // 为所有保留节点写入删除前坐标，防止布局算法重新分布导致位置突变。
      setDraggedPositions(() => {
        const next: Record<number, { x: number; y: number }> = {};
        for (const id of remainNodeIds) {
          const point = pointSnapshot.get(id);
          if (point) {
            next[id] = point;
          }
        }
        return next;
      });

      await refreshStats();
      showTip(`已成功移除节点 "${node.name}" 及其相连边。`);
    } catch (e) {
      showError(e instanceof Error ? e.message : '删除节点失败');
    } finally {
      setBusyAction('');
    }
  }

  useEffect(() => {
    refreshStats();
    setActionTip('输入实体词条后可直接搜索；若图谱中不存在，系统会自动调用 LLM 生成并入图。');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen bg-[#FAFAF5] py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-[1380px] mx-auto relative" onClick={() => setContextMenu(null)}>
        <div className="mb-6 flex flex-wrap items-center gap-3">
          {returnTo ? (
            <button
              onClick={() => navigate(returnTo, { state: returnState })}
              className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-[#FF9F45]"
            >
              <ArrowLeft size={16} />
              {returnLabel}
            </button>
          ) : null}
          <button
            onClick={() => navigate('/profile')}
            className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-[#FF9F45]"
          >
            <ArrowLeft size={16} />
            返回个人主页
          </button>
        </div>

        <div className="rounded-[16px] border border-orange-100 bg-white p-4 md:p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-[22px] font-bold text-gray-900">知识图谱可视化</h3>
          <p className="mt-1 text-sm text-gray-500">基于大模型自动抽取实体与关系，并实时渲染图结构</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleClearGraph}
            disabled={busyAction === 'clear'}
            className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600 hover:bg-red-100 disabled:opacity-50"
          >
            {busyAction === 'clear' ? <Loader2 size={16} className="animate-spin" /> : <AlertTriangle size={16} />}
            清空所有图谱库
          </button>
          <div className="flex items-center gap-2 rounded-xl border border-orange-100 bg-orange-50 px-3 py-2 text-sm text-orange-700">
            <Sparkles size={16} />
            LLM 图谱引擎已接入
          </div>
        </div>
      </div>

      {error ? (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          <AlertTriangle size={16} />
          {error}
        </div>
      ) : null}

      {actionTip && !error ? (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          {actionTip}
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[380px,1fr]">
        <div className="space-y-5">
          <div className="relative overflow-hidden rounded-2xl border border-orange-100 bg-gradient-to-br from-white via-orange-50/50 to-amber-50/80 p-5 shadow-[0_10px_28px_-18px_rgba(249,115,22,0.45)]">
            <div className="pointer-events-none absolute -right-8 -top-10 h-28 w-28 rounded-full bg-orange-200/30 blur-2xl" />
            <div className="pointer-events-none absolute -left-8 -bottom-12 h-24 w-24 rounded-full bg-amber-300/25 blur-2xl" />
            <div className="relative">
              <div className="mb-3 flex items-center justify-between gap-2">
                <p className="text-sm font-semibold tracking-wide text-gray-700">图谱概览</p>
                <button
                  type="button"
                  onClick={() => navigate('/knowledge-graph/entities')}
                  className="rounded-md border border-orange-200 bg-white px-2.5 py-1 text-xs font-semibold text-[#B75A00] hover:bg-orange-50"
                >
                  查看详情
                </button>
              </div>
              <div className="grid grid-cols-2 gap-3 text-center">
                <div className="rounded-xl border border-orange-200/60 bg-white/85 py-4 shadow-sm backdrop-blur-sm">
                  <div className="text-[30px] font-black leading-none text-orange-600">{stats?.total_entities ?? '-'}</div>
                  <div className="mt-2 text-xs font-medium tracking-wide text-orange-500">实体总数</div>
                </div>
                <div className="rounded-xl border border-sky-200/70 bg-white/85 py-4 shadow-sm backdrop-blur-sm">
                  <div className="text-[30px] font-black leading-none text-sky-600">{stats?.total_relations ?? '-'}</div>
                  <div className="mt-2 text-xs font-medium tracking-wide text-sky-500">关系总数</div>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-gray-200/90 bg-white p-5 shadow-[0_14px_40px_-26px_rgba(15,23,42,0.35)]">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-[17px] font-semibold text-gray-800">主题/实体搜索</p>
              <span className="rounded-full bg-orange-50 px-2.5 py-1 text-[11px] font-medium text-orange-600">智能检索</span>
            </div>
            <div className="grid grid-cols-[1fr_auto] gap-2.5">
              <input
                value={topicKeyword}
                onChange={(e) => setTopicKeyword(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleSearch();
                  }
                }}
                className="h-12 w-full rounded-xl border border-gray-300 bg-gradient-to-b from-white to-gray-50 px-4 text-[15px] text-gray-800 outline-none transition-all placeholder:text-gray-400 focus:border-orange-400 focus:ring-4 focus:ring-orange-100"
                placeholder="输入主题或实体关键词"
              />
              <button
                type="button"
                onClick={handleSearch}
                disabled={busyAction === 'search'}
                className="relative z-10 inline-flex h-12 min-w-[96px] shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-xl bg-gradient-to-r from-orange-500 to-orange-600 px-4 text-[22px] font-semibold text-white shadow-[0_10px_20px_-14px_rgba(234,88,12,0.95)] transition-all hover:from-orange-600 hover:to-orange-700 hover:shadow-[0_16px_26px_-16px_rgba(234,88,12,0.95)] active:scale-[0.98] disabled:cursor-not-allowed disabled:from-orange-300 disabled:to-orange-300 disabled:shadow-none"
                aria-label="主题或实体搜索"
              >
                {busyAction === 'search' ? (
                  <span className="inline-flex items-center gap-1.5 text-sm">
                    <Loader2 size={16} className="animate-spin" /> 搜索中
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 text-sm">
                    <Search size={16} /> 搜索
                  </span>
                )}
              </button>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-gray-500">支持主题词与实体词直搜，系统会自动补全知识并聚焦中心图谱。</p>
            {searchResults.length > 0 ? (
              <div className="mt-3 max-h-52 space-y-2.5 overflow-auto pr-1">
                {searchResults.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => handleNodeExpand(item)}
                    className="w-full rounded-xl border border-gray-200 bg-gradient-to-r from-white to-gray-50/80 px-3.5 py-2.5 text-left transition-all hover:-translate-y-[1px] hover:border-orange-300 hover:from-orange-50 hover:to-orange-100/40 hover:shadow-sm"
                  >
                    <div className="text-sm font-semibold text-gray-800">{item.name}</div>
                    <div className="mt-1 text-xs font-medium text-gray-500">{ENTITY_TYPE_ZH[item.entity_type] || item.entity_type}</div>
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-[#fcfcfa] p-3">
          <div className="mb-2 text-sm text-gray-500">
            节点 {graphData.nodes.length} / 边 {graphData.edges.length}
          </div>

          <div className="mb-3 rounded-lg border border-gray-100 bg-white p-3">
            <div className="mb-2 text-xs font-semibold text-gray-600">知识三元组（结构化）</div>
            {triples.length === 0 ? (
              <p className="text-xs text-gray-400">暂无三元组</p>
            ) : (
              <div className="max-h-28 space-y-1 overflow-auto">
                {triples.slice(0, 20).map((triple) => (
                  <div key={triple.id} className="text-xs text-gray-700">
                    {`<${triple.source}，${triple.relation}，${triple.target}>`}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="overflow-hidden rounded-lg border border-gray-100 bg-white relative cursor-grab active:cursor-grabbing group">
            <div className="absolute top-4 right-4 z-10 flex flex-col gap-2 opacity-80 group-hover:opacity-100 transition-opacity">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleClearCanvas();
                }}
                className="w-8 h-8 rounded-lg bg-red-50 border border-red-200 shadow-sm flex items-center justify-center text-red-600 hover:text-red-700 hover:border-red-300 hover:bg-red-100 transition-colors"
                title="清空画布"
              >
                <Trash2 size={16} />
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setZoomScale(prev => Math.min(prev * 1.2, 5));
                }}
                className="w-8 h-8 rounded-lg bg-white border border-gray-200 shadow-sm flex items-center justify-center text-gray-600 hover:text-orange-600 hover:border-orange-200 hover:bg-orange-50 transition-colors"
                title="放大"
              >
                <ZoomIn size={16} />
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setZoomScale(prev => Math.max(prev * 0.8, 0.2));
                }}
                className="w-8 h-8 rounded-lg bg-white border border-gray-200 shadow-sm flex items-center justify-center text-gray-600 hover:text-orange-600 hover:border-orange-200 hover:bg-orange-50 transition-colors"
                title="缩小"
              >
                <ZoomOut size={16} />
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setZoomScale(1);
                  setViewBoxOffset({ x: 0, y: 0 });
                }}
                className="w-8 h-8 rounded-lg bg-white border border-gray-200 shadow-sm flex items-center justify-center text-gray-600 hover:text-orange-600 hover:border-orange-200 hover:bg-orange-50 transition-colors"
                title="居中适应"
              >
                <Maximize size={16} />
              </button>
            </div>

            <svg
              ref={svgRef}
              viewBox={`${viewBoxOffset.x} ${viewBoxOffset.y} ${GRAPH_WIDTH / zoomScale} ${GRAPH_HEIGHT / zoomScale}`}
              className="h-[680px] w-full min-w-[780px]"
              onWheel={(e) => {
                // 拦截滚轮事件实现缩放
                if (e.deltaY === 0) return;
                e.preventDefault();

                const delta = e.deltaY > 0 ? 0.9 : 1.1; // 向上滚放大，向下滚缩小
                setZoomScale((prev) => {
                  let newScale = prev * delta;
                  // 限制最小最大缩放倍率
                  if (newScale < 0.2) newScale = 0.2;
                  if (newScale > 5) newScale = 5;
                  return newScale;
                });
              }}
              onMouseDown={(e) => {
                if (e.button !== 0) return; // 仅响应左键拖拽画布
                e.preventDefault();
                transformRef.current = {
                  isPanning: true,
                  startX: e.clientX,
                  startY: e.clientY,
                  currViewBoxX: viewBoxOffset.x,
                  currViewBoxY: viewBoxOffset.y
                };
                setIsPanning(true);
              }}
              onMouseMove={(e) => {
                if (transformRef.current.isPanning) {
                  // 画布平移
                  const dx = e.clientX - transformRef.current.startX;
                  const dy = e.clientY - transformRef.current.startY;
                  // 这里加一个系数可以调整拖拽速度灵敏度，一般等比就行
                  setViewBoxOffset({
                    x: transformRef.current.currViewBoxX - dx,
                    y: transformRef.current.currViewBoxY - dy
                  });
                  return;
                }

                if (draggingNodeId !== null && svgRef.current) {
                  // 节点拖拽
                  dragDidMove.current = true;
                  const CTM = svgRef.current.getScreenCTM();
                  if (!CTM) return;
                  const x = (e.clientX - CTM.e) / CTM.a;
                  const y = (e.clientY - CTM.f) / CTM.d;
                  setDraggedPositions((prev) => ({
                    ...prev,
                    [draggingNodeId]: { x, y },
                  }));
                }
              }}
              onMouseUp={() => {
                setDraggingNodeId(null);
                transformRef.current.isPanning = false;
                setIsPanning(false);
              }}
              onMouseLeave={() => {
                setDraggingNodeId(null);
                transformRef.current.isPanning = false;
                setIsPanning(false);
              }}
            >
              <defs>
                <linearGradient id="kgBg" x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor="#f8fafc" />
                  <stop offset="100%" stopColor="#f1f5f9" />
                </linearGradient>
                <pattern id="kgGrid" width="28" height="28" patternUnits="userSpaceOnUse">
                  <path d="M 28 0 L 0 0 0 28" fill="none" stroke="#e2e8f0" strokeOpacity="0.4" strokeWidth="1" />
                </pattern>
                <filter id="nodeShadow" x="-50%" y="-50%" width="200%" height="200%">
                  <feDropShadow dx="0" dy="2" stdDeviation="2" floodColor="#0f172a" floodOpacity="0.18" />
                </filter>
                <marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
                  <path d="M0,0 L6,3 L0,6 Z" fill="#94a3b8" />
                </marker>
              </defs>

              <rect x="-5000" y="-5000" width="10000" height="10000" fill="url(#kgBg)" />
              <rect x="-5000" y="-5000" width="10000" height="10000" fill="url(#kgGrid)" />

              {uniqueEdges.map((edge, edgeIndex) => {
                const source = pointMap.get(edge.source_entity_id);
                const target = pointMap.get(edge.target_entity_id);
                if (!source || !target) return null;

                const edgeColor = RELATION_COLORS[edge.relation_type] || '#94a3b8';
                const dx = target.x - source.x;
                const dy = target.y - source.y;
                const length = Math.max(1, Math.sqrt(dx * dx + dy * dy));
                const nx = -dy / length;
                const ny = dx / length;
                const lane = edgeCurveMeta.get(edgeIndex);
                const laneOffset = lane
                  ? (lane.laneIndex - (lane.laneTotal - 1) / 2) * 24
                  : 0;

                const mx = (source.x + target.x) / 2;
                const my = (source.y + target.y) / 2;
                const cx = mx + nx * laneOffset;
                const cy = my + ny * laneOffset;
                
                const ctrlX = mx + nx * (laneOffset * 2);
                const ctrlY = my + ny * (laneOffset * 2);

                // 计算目标端点位置，使其恰好缩在目标的圆圈边缘之外，不遮挡箭头
                const isSourceSelected = selectedNodeId === source.id;
                const sourceRadius = isSourceSelected ? 20 : 16;
                const sourceOffset = sourceRadius + 2;
                const isTargetSelected = selectedNodeId === target.id;
                const targetRadius = isTargetSelected ? 20 : 16;
                const arrowOffset = targetRadius + 3; // 圆圈半径 + 描边偏移

                let startX = source.x;
                let startY = source.y;

                if (laneOffset === 0) {
                  startX = source.x + (dx / length) * sourceOffset;
                  startY = source.y + (dy / length) * sourceOffset;
                } else {
                  const sDx = ctrlX - source.x;
                  const sDy = ctrlY - source.y;
                  const sLen = Math.max(1, Math.sqrt(sDx * sDx + sDy * sDy));
                  startX = source.x + (sDx / sLen) * sourceOffset;
                  startY = source.y + (sDy / sLen) * sourceOffset;
                }

                let endX = target.x;
                let endY = target.y;

                if (laneOffset === 0) {
                  endX = target.x - (dx / length) * arrowOffset;
                  endY = target.y - (dy / length) * arrowOffset;
                } else {
                  const tDx = target.x - ctrlX;
                  const tDy = target.y - ctrlY;
                  const tLen = Math.max(1, Math.sqrt(tDx * tDx + tDy * tDy));
                  endX = target.x - (tDx / tLen) * arrowOffset;
                  endY = target.y - (tDy / tLen) * arrowOffset;
                }

                const path = laneOffset === 0 
                  ? `M ${startX} ${startY} L ${endX} ${endY}`
                  : `M ${startX} ${startY} Q ${ctrlX} ${ctrlY} ${endX} ${endY}`;

                return (
                  <g key={edge.id}>
                    <path
                      d={path}
                      stroke={edgeColor}
                      strokeOpacity={0.7}
                      strokeWidth={1.8}
                      fill="none"
                      markerEnd="url(#arrow)"
                    />
                    <text
                      x={cx}
                      y={cy - 6}
                      fill="#334155"
                      fontSize="11"
                      textAnchor="middle"
                      stroke="#ffffff"
                      strokeWidth="3"
                      paintOrder="stroke"
                    >
                      {relationDisplayText(edge)}
                    </text>
                  </g>
                );
              })}

              {points.map((point) => {
                const node = point.node;
                const isSelected = selectedNodeId === node.id;
                const color = ENTITY_COLORS[node.entity_type] || '#f97316';

                return (
                  <g
                    key={node.id}
                    onMouseDown={(e) => {
                      if (e.button === 2) return; // ignore right click for drag
                      e.preventDefault();
                      e.stopPropagation(); // 阻止冒泡，避免触发 SVG 的画布拖拽
                      setDraggingNodeId(node.id);
                      dragDidMove.current = false;
                    }}
                    onContextMenu={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setContextMenu({
                        x: e.clientX,
                        y: e.clientY - 60, // approximate offset from viewport, or handle via screen
                        nodeId: node.id
                      });
                    }}
                    onClick={(e) => {
                      if (!dragDidMove.current && e.button !== 2) {
                        setSelectedNodeId(node.id);
                      }
                    }}
                    className="cursor-pointer"
                  >
                    <circle
                      cx={point.x}
                      cy={point.y}
                      r={isSelected ? 20 : 16}
                      fill={color}
                      fillOpacity={isSelected ? 0.92 : 0.82}
                      stroke={isSelected ? '#111827' : '#ffffff'}
                      strokeWidth={isSelected ? 2.5 : 1.5}
                      filter="url(#nodeShadow)"
                    />
                    <text
                      x={point.x}
                      y={point.y + 34}
                      fontSize="12"
                      fill="#1f2937"
                      textAnchor="middle"
                    >
                      {node.name.length > 10 ? `${node.name.slice(0, 10)}...` : node.name}
                    </text>
                  </g>
                );
              })}

              {loadingGraph ? (
                <text x={GRAPH_WIDTH / 2} y={GRAPH_HEIGHT / 2} textAnchor="middle" fill="#6b7280" fontSize="15">
                  图谱加载中...
                </text>
              ) : null}
            </svg>
          </div>

          {selectedNode ? (
            <div className="mt-3 rounded-lg border border-orange-100 bg-orange-50 p-4 text-sm flex justify-between items-start shadow-sm">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg font-bold text-gray-900">{selectedNode.name}</span>
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-white text-orange-600 border border-orange-200">
                    {ENTITY_TYPE_ZH[selectedNode.entity_type] || selectedNode.entity_type}
                  </span>
                </div>
                <div className="mt-2 text-gray-700 leading-relaxed max-w-3xl">
                  {selectedNode.description || '暂无详细描述。你可以点击“扩展该节点邻居”来通过大模型挖掘更多关于该实体的科学知识。'}
                </div>
                <div className="mt-4 flex gap-3">
                  <button
                    onClick={() => handleNodeExpand(selectedNode)}
                    className="rounded-md bg-white px-3 py-1.5 text-xs font-semibold text-orange-700 ring-1 ring-orange-200 hover:bg-orange-100 transition-colors flex items-center gap-1"
                  >
                    {busyAction === `expand-${selectedNode.id}` ? (
                      <><Loader2 size={14} className="animate-spin" /> 展开中...</>
                    ) : (
                      <><Sparkles size={14} /> 扩展该节点邻居</>
                    )}
                  </button>
                  <button
                    onClick={() => handleDeleteNode(selectedNode.id)}
                    className="rounded-md bg-white px-3 py-1.5 text-xs font-semibold text-red-600 ring-1 ring-red-200 hover:bg-red-50 transition-colors"
                  >
                    删除节点
                  </button>
                </div>
              </div>
            </div>
          ) : null}
          
          {/* Right-click Context Menu */}
          {contextMenu && (
            <div
              className="absolute z-50 bg-white border border-gray-200 shadow-lg rounded-md overflow-hidden"
              style={{ top: contextMenu.y, left: contextMenu.x }}
            >
              <button
                className="w-full px-4 py-2 text-sm text-red-600 hover:bg-red-50 text-left font-medium"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteNode(contextMenu.nodeId);
                  setContextMenu(null);
                }}
              >
                删除节点
              </button>
            </div>
          )}
        </div>
      </div>
        </div>
      </div>
    </div>
  );
}
