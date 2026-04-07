"""
知识图谱计算工具
集成NetworkX进行图计算和分析
"""
import json
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from collections import deque

from models import models

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    nx = None


def _safe_json_loads(text: str, fallback: Any):
    """安全加载JSON"""
    try:
        return json.loads(text) if text else fallback
    except Exception:
        return fallback


class KnowledgeGraphComputer:
    """知识图谱计算引擎"""

    def __init__(self, db: Session):
        self.db = db
        self.graph = None
        if HAS_NETWORKX:
            self.graph = self._load_graph()

    def _load_graph(self) -> Optional[nx.DiGraph]:
        """从数据库加载图到内存（有向图）"""
        if not HAS_NETWORKX:
            return None

        G = nx.DiGraph()

        # 加载所有实体作为节点
        entities = self.db.query(models.KnowledgeGraphEntity).all()
        for entity in entities:
            G.add_node(
                entity.id,
                name=entity.name,
                type=entity.entity_type,
                description=entity.description,
                confidence=entity.confidence,
            )

        # 加载所有关系作为边
        relations = self.db.query(models.KnowledgeGraphRelation).all()
        for rel in relations:
            G.add_edge(
                rel.source_entity_id,
                rel.target_entity_id,
                relation_type=rel.relation_type,
                description=rel.description,
                confidence=rel.confidence,
            )

        return G

    def refresh_graph(self):
        """刷新图数据"""
        if HAS_NETWORKX:
            self.graph = self._load_graph()

    def is_available(self) -> bool:
        """检查NetworkX是否可用"""
        return HAS_NETWORKX and self.graph is not None

    def find_shortest_path(
        self,
        source_id: int,
        target_id: int,
        max_depth: int = 3
    ) -> Tuple[Optional[List[int]], List]:
        """
        寻找两个实体之间的最短路径
        返回 (节点ID列表, 边对象列表)
        """
        if not self.is_available():
            return None, []

        if source_id not in self.graph or target_id not in self.graph:
            return None, []

        try:
            # 使用BFS找最短路径（无权）
            path = nx.shortest_path(
                self.graph,
                source=source_id,
                target=target_id,
            )

            if len(path) - 1 > max_depth:
                return None, []

            # 获取路径上的边
            edges = []
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                edge_data = self.graph.get_edge_data(u, v)
                # 从数据库获取完整的边对象
                rel = self.db.query(models.KnowledgeGraphRelation).filter(
                    models.KnowledgeGraphRelation.source_entity_id == u,
                    models.KnowledgeGraphRelation.target_entity_id == v,
                ).first()
                if rel:
                    edges.append(rel)

            return path, edges

        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None, []

    def find_central_entities(self, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        发现核心实体（基于PageRank）
        """
        if not self.is_available():
            return []

        try:
            # PageRank计算
            pagerank = nx.pagerank(self.graph.to_undirected(), alpha=0.85)

            # 排序并取前top_k
            sorted_nodes = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)[:top_k]

            result = []
            for node_id, score in sorted_nodes:
                entity = self.db.query(models.KnowledgeGraphEntity).filter(
                    models.KnowledgeGraphEntity.id == node_id
                ).first()
                if entity:
                    result.append({
                        "id": entity.id,
                        "name": entity.name,
                        "type": entity.entity_type,
                        "description": entity.description,
                        "pagerank": score,
                        "confidence": entity.confidence,
                    })

            return result

        except Exception as e:
            print(f"[find_central_entities] 错误: {e}")
            return []

    def find_communities(self) -> List[List[int]]:
        """
        社区发现（知识聚类）
        使用Louvain算法（如果安装了python-louvain）
        否则使用简单的连通分量
        """
        if not self.is_available():
            return []

        try:
            # 先尝试Louvain算法（需要python-louvain包）
            try:
                import community as community_louvain
                partition = community_louvain.best_partition(self.graph.to_undirected())

                # 按社区分组
                communities: Dict[int, List[int]] = {}
                for node_id, comm_id in partition.items():
                    if comm_id not in communities:
                        communities[comm_id] = []
                    communities[comm_id].append(node_id)

                return list(communities.values())

            except ImportError:
                # 回退到连通分量
                components = list(nx.connected_components(self.graph.to_undirected()))
                return [list(comp) for comp in components]

        except Exception as e:
            print(f"[find_communities] 错误: {e}")
            return []

    def get_subgraph_around_topic(
        self,
        topic_entity_ids: List[int],
        max_nodes: int = 100,
        max_depth: int = 2
    ) -> Optional[nx.DiGraph]:
        """
        获取主题相关的子图
        """
        if not self.is_available():
            return None

        # BFS收集节点
        nodes = set(topic_entity_ids)
        queue = deque([(eid, 0) for eid in topic_entity_ids])

        while queue and len(nodes) < max_nodes:
            current_id, depth = queue.popleft()

            if depth >= max_depth or current_id not in self.graph:
                continue

            # 获取邻居
            neighbors = list(self.graph.neighbors(current_id)) + list(self.graph.predecessors(current_id))

            for neighbor in neighbors:
                if neighbor not in nodes and len(nodes) < max_nodes:
                    nodes.add(neighbor)
                    queue.append((neighbor, depth + 1))

        return self.graph.subgraph(nodes)

    def get_entity_neighbors(
        self,
        entity_id: int,
        relation_type: Optional[str] = None,
        max_depth: int = 2,
        limit: int = 50
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        获取实体的邻居节点和边
        返回 (节点列表, 边列表)
        """
        if not self.is_available():
            # 回退到数据库查询
            return self._get_neighbors_from_db(entity_id, relation_type, max_depth, limit)

        if entity_id not in self.graph:
            return [], []

        # BFS收集
        nodes = {}
        edges = []
        queue = deque([(entity_id, 0)])

        # 添加起始节点
        start_entity = self.db.query(models.KnowledgeGraphEntity).filter(
            models.KnowledgeGraphEntity.id == entity_id
        ).first()
        if start_entity:
            nodes[entity_id] = {
                "id": start_entity.id,
                "name": start_entity.name,
                "entity_type": start_entity.entity_type,
                "description": start_entity.description,
                "confidence": start_entity.confidence,
            }

        while queue and len(nodes) < limit:
            current_id, depth = queue.popleft()

            if depth >= max_depth:
                continue

            # 处理出边
            for neighbor in self.graph.neighbors(current_id):
                edge_data = self.graph.get_edge_data(current_id, neighbor)

                if relation_type and edge_data.get("relation_type") != relation_type:
                    continue

                # 获取完整实体信息
                if neighbor not in nodes:
                    entity = self.db.query(models.KnowledgeGraphEntity).filter(
                        models.KnowledgeGraphEntity.id == neighbor
                    ).first()
                    if entity and len(nodes) < limit:
                        nodes[neighbor] = {
                            "id": entity.id,
                            "name": entity.name,
                            "entity_type": entity.entity_type,
                            "description": entity.description,
                            "confidence": entity.confidence,
                        }
                        queue.append((neighbor, depth + 1))

                # 获取边信息
                rel = self.db.query(models.KnowledgeGraphRelation).filter(
                    models.KnowledgeGraphRelation.source_entity_id == current_id,
                    models.KnowledgeGraphRelation.target_entity_id == neighbor,
                ).first()
                if rel:
                    edges.append({
                        "id": rel.id,
                        "source_entity_id": rel.source_entity_id,
                        "target_entity_id": rel.target_entity_id,
                        "relation_type": rel.relation_type,
                        "description": rel.description,
                        "confidence": rel.confidence,
                    })

            # 处理入边
            for neighbor in self.graph.predecessors(current_id):
                edge_data = self.graph.get_edge_data(neighbor, current_id)

                if relation_type and edge_data.get("relation_type") != relation_type:
                    continue

                # 获取完整实体信息
                if neighbor not in nodes:
                    entity = self.db.query(models.KnowledgeGraphEntity).filter(
                        models.KnowledgeGraphEntity.id == neighbor
                    ).first()
                    if entity and len(nodes) < limit:
                        nodes[neighbor] = {
                            "id": entity.id,
                            "name": entity.name,
                            "entity_type": entity.entity_type,
                            "description": entity.description,
                            "confidence": entity.confidence,
                        }
                        queue.append((neighbor, depth + 1))

                # 获取边信息
                rel = self.db.query(models.KnowledgeGraphRelation).filter(
                    models.KnowledgeGraphRelation.source_entity_id == neighbor,
                    models.KnowledgeGraphRelation.target_entity_id == current_id,
                ).first()
                if rel:
                    edges.append({
                        "id": rel.id,
                        "source_entity_id": rel.source_entity_id,
                        "target_entity_id": rel.target_entity_id,
                        "relation_type": rel.relation_type,
                        "description": rel.description,
                        "confidence": rel.confidence,
                    })

        return list(nodes.values()), edges

    def _get_neighbors_from_db(
        self,
        entity_id: int,
        relation_type: Optional[str] = None,
        max_depth: int = 2,
        limit: int = 50
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        不使用NetworkX的回退方案，直接从数据库查询
        仅限1层深度
        """
        nodes = {}
        edges = []

        # 添加起始节点
        start_entity = self.db.query(models.KnowledgeGraphEntity).filter(
            models.KnowledgeGraphEntity.id == entity_id
        ).first()
        if not start_entity:
            return [], []

        nodes[entity_id] = {
            "id": start_entity.id,
            "name": start_entity.name,
            "entity_type": start_entity.entity_type,
            "description": start_entity.description,
            "confidence": start_entity.confidence,
        }

        # 查询出边
        query_builder = self.db.query(models.KnowledgeGraphRelation).filter(
            models.KnowledgeGraphRelation.source_entity_id == entity_id
        )
        if relation_type:
            query_builder = query_builder.filter(
                models.KnowledgeGraphRelation.relation_type == relation_type
            )

        out_relations = query_builder.limit(limit // 2).all()

        for rel in out_relations:
            if rel.target_entity_id not in nodes and len(nodes) < limit:
                entity = self.db.query(models.KnowledgeGraphEntity).filter(
                    models.KnowledgeGraphEntity.id == rel.target_entity_id
                ).first()
                if entity:
                    nodes[rel.target_entity_id] = {
                        "id": entity.id,
                        "name": entity.name,
                        "entity_type": entity.entity_type,
                        "description": entity.description,
                        "confidence": entity.confidence,
                    }

            edges.append({
                "id": rel.id,
                "source_entity_id": rel.source_entity_id,
                "target_entity_id": rel.target_entity_id,
                "relation_type": rel.relation_type,
                "description": rel.description,
                "confidence": rel.confidence,
            })

        # 查询入边
        query_builder = self.db.query(models.KnowledgeGraphRelation).filter(
            models.KnowledgeGraphRelation.target_entity_id == entity_id
        )
        if relation_type:
            query_builder = query_builder.filter(
                models.KnowledgeGraphRelation.relation_type == relation_type
            )

        in_relations = query_builder.limit(limit // 2).all()

        for rel in in_relations:
            if rel.source_entity_id not in nodes and len(nodes) < limit:
                entity = self.db.query(models.KnowledgeGraphEntity).filter(
                    models.KnowledgeGraphEntity.id == rel.source_entity_id
                ).first()
                if entity:
                    nodes[rel.source_entity_id] = {
                        "id": entity.id,
                        "name": entity.name,
                        "entity_type": entity.entity_type,
                        "description": entity.description,
                        "confidence": entity.confidence,
                    }

            edges.append({
                "id": rel.id,
                "source_entity_id": rel.source_entity_id,
                "target_entity_id": rel.target_entity_id,
                "relation_type": rel.relation_type,
                "description": rel.description,
                "confidence": rel.confidence,
            })

        return list(nodes.values()), edges
