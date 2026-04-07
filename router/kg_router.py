"""
知识图谱API路由
提供实体和关系的CRUD、检索、子图等功能
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session

from utils.database import get_db
from models import models, schemas
from utils.response import success, error
from utils.wikipedia_client import search_wikipedia
import json

router = APIRouter(tags=["Knowledge Graph"])


def _safe_json_loads(text: str, fallback: Any):
    """安全加载JSON"""
    try:
        return json.loads(text) if text else fallback
    except Exception:
        return fallback


def _safe_json_dumps(data: Any) -> str:
    """安全序列化JSON"""
    try:
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return "[]"


def _entity_to_dict(entity: models.KnowledgeGraphEntity) -> Dict[str, Any]:
    """实体模型转字典"""
    return {
        "id": entity.id,
        "name": entity.name,
        "entity_type": entity.entity_type,
        "description": entity.description,
        "aliases": _safe_json_loads(entity.aliases, []),
        "properties": _safe_json_loads(entity.properties, None),
        "source_document_id": entity.source_document_id,
        "confidence": entity.confidence,
        "created_at": entity.created_at.isoformat() if entity.created_at else None,
        "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
    }


def _relation_to_dict(relation: models.KnowledgeGraphRelation) -> Dict[str, Any]:
    """关系模型转字典"""
    return {
        "id": relation.id,
        "source_entity_id": relation.source_entity_id,
        "target_entity_id": relation.target_entity_id,
        "relation_type": relation.relation_type,
        "description": relation.description,
        "properties": _safe_json_loads(relation.properties, None),
        "source_document_id": relation.source_document_id,
        "confidence": relation.confidence,
        "created_at": relation.created_at.isoformat() if relation.created_at else None,
    }


# =============== 实体 CRUD ===============

@router.get("/kg/entities")
def list_entities(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    entity_type: Optional[str] = Query(None, description="实体类型筛选"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="最低置信度"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
):
    """列出实体列表（支持分页和筛选）"""
    query_builder = db.query(models.KnowledgeGraphEntity)

    filters = []
    if entity_type:
        filters.append(models.KnowledgeGraphEntity.entity_type == entity_type)
    if min_confidence is not None:
        filters.append(models.KnowledgeGraphEntity.confidence >= min_confidence)
    if search:
        filters.append(
            or_(
                models.KnowledgeGraphEntity.name.contains(search),
                models.KnowledgeGraphEntity.description.contains(search),
            )
        )

    if filters:
        query_builder = query_builder.filter(and_(*filters))

    total = query_builder.count()
    offset = (page - 1) * page_size
    entities = query_builder.order_by(models.KnowledgeGraphEntity.created_at.desc()).offset(offset).limit(page_size).all()

    items = [_entity_to_dict(e) for e in entities]
    total_pages = (total + page_size - 1) // page_size

    return success(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    })


@router.get("/kg/wikipedia/search")
def search_wikipedia_pages(
    query: str = Query(..., min_length=1, description="搜索关键词"),
    language: str = Query("zh", description="语言代码"),
    limit: int = Query(5, ge=1, le=20, description="返回数量"),
):
    """搜索维基百科词条（用于辅助构建图谱）"""
    results = search_wikipedia(query=query, limit=limit, language=language)
    return success(data={"query": query, "results": results, "total": len(results)})


@router.get("/kg/entities/{entity_id}")
def get_entity(entity_id: int, db: Session = Depends(get_db)):
    """获取单个实体详情"""
    entity = db.query(models.KnowledgeGraphEntity).filter(
        models.KnowledgeGraphEntity.id == entity_id
    ).first()
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")
    return success(data=_entity_to_dict(entity))


@router.post("/kg/entities")
def create_entity(
    request: schemas.KnowledgeGraphEntityCreate,
    db: Session = Depends(get_db),
):
    """创建新实体"""
    try:
        entity = models.KnowledgeGraphEntity(
            name=request.name,
            entity_type=request.entity_type,
            description=request.description,
            aliases=_safe_json_dumps(request.aliases) if request.aliases else None,
            properties=_safe_json_dumps(request.properties) if request.properties else None,
            source_document_id=request.source_document_id,
            confidence=request.confidence,
        )
        db.add(entity)
        db.flush()

        # 生成向量嵌入
        from utils.llm_client import llm_client
        embedding_text = f"{request.name} {request.description or ''}"
        embedding = llm_client.generate_embedding(embedding_text)
        embedding_row = models.KnowledgeGraphEntityEmbedding(
            entity_id=entity.id,
            embedding=_safe_json_dumps(embedding),
        )
        db.add(embedding_row)

        db.commit()
        db.refresh(entity)

        return success(
            data=_entity_to_dict(entity),
            msg="实体创建成功",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/kg/entities/{entity_id}")
def update_entity(
    entity_id: int,
    request: schemas.KnowledgeGraphEntityUpdate,
    db: Session = Depends(get_db),
):
    """更新实体"""
    entity = db.query(models.KnowledgeGraphEntity).filter(
        models.KnowledgeGraphEntity.id == entity_id
    ).first()
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ["aliases", "properties"]:
            setattr(entity, field, _safe_json_dumps(value))
        else:
            setattr(entity, field, value)

    db.commit()
    db.refresh(entity)
    return success(data=_entity_to_dict(entity), msg="实体更新成功")


@router.delete("/kg/entities/{entity_id}")
def delete_entity(entity_id: int, db: Session = Depends(get_db)):
    """删除实体及其关系和向量"""
    entity = db.query(models.KnowledgeGraphEntity).filter(
        models.KnowledgeGraphEntity.id == entity_id
    ).first()
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

    # 删除关联的关系
    db.query(models.KnowledgeGraphRelation).filter(
        or_(
            models.KnowledgeGraphRelation.source_entity_id == entity_id,
            models.KnowledgeGraphRelation.target_entity_id == entity_id,
        )
    ).delete()

    # 删除关联的向量
    db.query(models.KnowledgeGraphEntityEmbedding).filter(
        models.KnowledgeGraphEntityEmbedding.entity_id == entity_id
    ).delete()

    db.delete(entity)
    db.commit()

    return success(data={"entity_id": entity_id}, msg="实体删除成功")


# =============== 关系 CRUD ===============

@router.get("/kg/relations")
def list_relations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    relation_type: Optional[str] = None,
    source_entity_id: Optional[int] = None,
    target_entity_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """列出关系列表"""
    query_builder = db.query(models.KnowledgeGraphRelation)

    filters = []
    if relation_type:
        filters.append(models.KnowledgeGraphRelation.relation_type == relation_type)
    if source_entity_id:
        filters.append(models.KnowledgeGraphRelation.source_entity_id == source_entity_id)
    if target_entity_id:
        filters.append(models.KnowledgeGraphRelation.target_entity_id == target_entity_id)

    if filters:
        query_builder = query_builder.filter(and_(*filters))

    total = query_builder.count()
    offset = (page - 1) * page_size
    relations = query_builder.order_by(models.KnowledgeGraphRelation.created_at.desc()).offset(offset).limit(page_size).all()

    items = [_relation_to_dict(r) for r in relations]
    total_pages = (total + page_size - 1) // page_size

    return success(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    })


@router.get("/kg/relations/{relation_id}")
def get_relation(relation_id: int, db: Session = Depends(get_db)):
    """获取单个关系详情"""
    relation = db.query(models.KnowledgeGraphRelation).filter(
        models.KnowledgeGraphRelation.id == relation_id
    ).first()
    if not relation:
        raise HTTPException(status_code=404, detail="关系不存在")
    return success(data=_relation_to_dict(relation))


@router.post("/kg/relations")
def create_relation(
    request: schemas.KnowledgeGraphRelationCreate,
    db: Session = Depends(get_db),
):
    """创建新关系"""
    # 验证源实体和目标实体存在
    source = db.query(models.KnowledgeGraphEntity).filter(
        models.KnowledgeGraphEntity.id == request.source_entity_id
    ).first()
    target = db.query(models.KnowledgeGraphEntity).filter(
        models.KnowledgeGraphEntity.id == request.target_entity_id
    ).first()

    if not source:
        raise HTTPException(status_code=404, detail="源实体不存在")
    if not target:
        raise HTTPException(status_code=404, detail="目标实体不存在")

    relation = models.KnowledgeGraphRelation(
        source_entity_id=request.source_entity_id,
        target_entity_id=request.target_entity_id,
        relation_type=request.relation_type,
        description=request.description,
        properties=_safe_json_dumps(request.properties) if request.properties else None,
        source_document_id=request.source_document_id,
        confidence=request.confidence,
    )
    db.add(relation)
    db.commit()
    db.refresh(relation)

    return success(data=_relation_to_dict(relation), msg="关系创建成功")


@router.put("/kg/relations/{relation_id}")
def update_relation(
    relation_id: int,
    request: schemas.KnowledgeGraphRelationUpdate,
    db: Session = Depends(get_db),
):
    """更新关系"""
    relation = db.query(models.KnowledgeGraphRelation).filter(
        models.KnowledgeGraphRelation.id == relation_id
    ).first()
    if not relation:
        raise HTTPException(status_code=404, detail="关系不存在")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "properties":
            setattr(relation, field, _safe_json_dumps(value))
        else:
            setattr(relation, field, value)

    db.commit()
    db.refresh(relation)
    return success(data=_relation_to_dict(relation), msg="关系更新成功")


@router.delete("/kg/relations/{relation_id}")
def delete_relation(relation_id: int, db: Session = Depends(get_db)):
    """删除关系"""
    relation = db.query(models.KnowledgeGraphRelation).filter(
        models.KnowledgeGraphRelation.id == relation_id
    ).first()
    if not relation:
        raise HTTPException(status_code=404, detail="关系不存在")

    db.delete(relation)
    db.commit()
    return success(data={"relation_id": relation_id}, msg="关系删除成功")


@router.delete("/kg/clear")
def clear_knowledge_graph(confirm: bool = Query(False, description="确认清空图谱库"), db: Session = Depends(get_db)):
    """清空整份知识图谱的所有实体与关系、词嵌入。此操作不可逆！"""
    if not confirm:
        raise HTTPException(status_code=400, detail="必须设置 confirm=true 才能执行删除操作")

    try:
        # 删除所有关系
        db.query(models.KnowledgeGraphRelation).delete()
        # 删除所有实体 embedding
        db.query(models.KnowledgeGraphEntityEmbedding).delete()
        # 删除所有实体
        db.query(models.KnowledgeGraphEntity).delete()

        db.commit()
        return success(data={}, msg="知识图谱已清空")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"清空知识图谱失败: {str(e)}")


# =============== 图谱检索 ===============

@router.post("/kg/entities/search")
def search_entities(
    request: schemas.KnowledgeGraphEntitySearchRequest,
    db: Session = Depends(get_db),
):
    """搜索实体（支持语义搜索和关键词搜索）"""
    query = request.query.strip()
    if not query:
        return success(data={"query": query, "results": [], "total": 0})

    # 先做关键词搜索
    query_builder = db.query(models.KnowledgeGraphEntity)
    keyword_results = query_builder.filter(
        or_(
            models.KnowledgeGraphEntity.name.contains(query),
            models.KnowledgeGraphEntity.description.contains(query),
        )
    ).limit(request.limit).all()

    # 做语义搜索
    from utils.llm_client import llm_client
    from utils.fact_rag import cosine_similarity

    try:
        query_embedding = llm_client.generate_embedding(query)

        # 获取所有实体的向量
        embeddings = db.query(models.KnowledgeGraphEntityEmbedding).all()
        scored_entities = []

        for emb_row in embeddings:
            chunk_embedding = _safe_json_loads(emb_row.embedding, [])
            score = cosine_similarity(query_embedding, chunk_embedding)
            if score > 0.5:
                entity = db.query(models.KnowledgeGraphEntity).filter(
                    models.KnowledgeGraphEntity.id == emb_row.entity_id
                ).first()
                if entity:
                    scored_entities.append((entity, score))

        # 按相似度排序
        scored_entities.sort(key=lambda x: x[1], reverse=True)
        semantic_results = [e for e, s in scored_entities[:request.limit]]

        # 合并结果（去重）
        seen_ids = set()
        all_results = []

        for entity in keyword_results + semantic_results:
            if entity.id not in seen_ids:
                seen_ids.add(entity.id)
                if request.min_confidence and entity.confidence < request.min_confidence:
                    continue
                if request.entity_type and entity.entity_type != request.entity_type:
                    continue
                all_results.append(_entity_to_dict(entity))

        return success(data={
            "query": query,
            "results": all_results[:request.limit],
            "total": len(all_results),
        })

    except Exception as e:
        # 如果向量搜索失败，回退到关键词搜索
        filtered = [_entity_to_dict(e) for e in keyword_results]
        return success(data={
            "query": query,
            "results": filtered[:request.limit],
            "total": len(filtered),
        })


@router.get("/kg/entities/{entity_id}/neighbors")
def get_entity_neighbors(
    entity_id: int,
    relation_type: Optional[str] = None,
    max_depth: int = Query(2, ge=1, le=3),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """获取实体的邻居节点（用于可视化）"""
    entity = db.query(models.KnowledgeGraphEntity).filter(
        models.KnowledgeGraphEntity.id == entity_id
    ).first()
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")

    # 简单的广度优先搜索
    nodes = {}
    edges = []
    queue = [(entity_id, 0)]
    nodes[entity_id] = _entity_to_dict(entity)

    while queue and len(nodes) < limit:
        current_id, depth = queue.pop(0)
        if depth >= max_depth:
            continue

        # 获取从当前节点出发的关系
        query_builder = db.query(models.KnowledgeGraphRelation).filter(
            models.KnowledgeGraphRelation.source_entity_id == current_id
        )
        if relation_type:
            query_builder = query_builder.filter(
                models.KnowledgeGraphRelation.relation_type == relation_type
            )

        out_relations = query_builder.all()

        for rel in out_relations:
            if rel.target_entity_id not in nodes:
                target = db.query(models.KnowledgeGraphEntity).filter(
                    models.KnowledgeGraphEntity.id == rel.target_entity_id
                ).first()
                if target and len(nodes) < limit:
                    nodes[rel.target_entity_id] = _entity_to_dict(target)
                    queue.append((rel.target_entity_id, depth + 1))

            edges.append(_relation_to_dict(rel))

        # 获取指向当前节点的关系
        query_builder = db.query(models.KnowledgeGraphRelation).filter(
            models.KnowledgeGraphRelation.target_entity_id == current_id
        )
        if relation_type:
            query_builder = query_builder.filter(
                models.KnowledgeGraphRelation.relation_type == relation_type
            )

        in_relations = query_builder.all()

        for rel in in_relations:
            if rel.source_entity_id not in nodes:
                source = db.query(models.KnowledgeGraphEntity).filter(
                    models.KnowledgeGraphEntity.id == rel.source_entity_id
                ).first()
                if source and len(nodes) < limit:
                    nodes[rel.source_entity_id] = _entity_to_dict(source)
                    queue.append((rel.source_entity_id, depth + 1))

            edges.append(_relation_to_dict(rel))

    return success(data={
        "nodes": list(nodes.values()),
        "edges": edges,
    })


@router.get("/kg/concept/{concept_name}/neighbors")
def get_concept_neighbors_by_name(
    concept_name: str,
    max_depth: int = Query(2, ge=1, le=3),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """按概念名称获取相邻概念子图，便于在文章中直接使用概念字符串查询。"""
    entity = db.query(models.KnowledgeGraphEntity).filter(
        models.KnowledgeGraphEntity.name == concept_name.strip()
    ).first()

    if not entity:
        entity = db.query(models.KnowledgeGraphEntity).filter(
            models.KnowledgeGraphEntity.name.contains(concept_name.strip())
        ).first()

    if not entity:
        raise HTTPException(status_code=404, detail="概念不存在")

    return get_entity_neighbors(
        entity_id=entity.id,
        relation_type=None,
        max_depth=max_depth,
        limit=limit,
        db=db,
    )


@router.get("/kg/subgraph")
def get_subgraph(
    topic: Optional[str] = None,
    entity_ids: Optional[str] = Query(None, description="实体ID列表，逗号分隔"),
    max_nodes: int = Query(100, ge=10, le=500),
    db: Session = Depends(get_db),
):
    """获取主题相关的子图"""
    target_entity_ids = []

    if entity_ids:
        target_entity_ids = [int(x.strip()) for x in entity_ids.split(",") if x.strip()]
    elif topic:
        # 搜索相关实体
        query_builder = db.query(models.KnowledgeGraphEntity).filter(
            or_(
                models.KnowledgeGraphEntity.name.contains(topic),
                models.KnowledgeGraphEntity.description.contains(topic),
            )
        ).limit(20)
        entities = query_builder.all()
        target_entity_ids = [e.id for e in entities]

    if not target_entity_ids:
        return success(data={"nodes": [], "edges": []})

    # 获取这些实体之间的关系
    nodes = {}
    edges = []

    # 先加载所有目标实体
    for eid in target_entity_ids:
        entity = db.query(models.KnowledgeGraphEntity).filter(
            models.KnowledgeGraphEntity.id == eid
        ).first()
        if entity:
            nodes[eid] = _entity_to_dict(entity)

    # 获取含有至少一个目标实体的关系，这样可以自动扩展相关子图网络而不只是限制在这几个实体互相缠绕
    relations_query = db.query(models.KnowledgeGraphRelation).filter(
        or_(
            models.KnowledgeGraphRelation.source_entity_id.in_(target_entity_ids),
            models.KnowledgeGraphRelation.target_entity_id.in_(target_entity_ids),
        )
    ).limit(max_nodes * 2).all()

    # 查漏补缺：将被拉出来的外围节点也一并加入 nodes 中
    extra_entity_ids = set()
    for rel in relations_query:
        extra_entity_ids.add(rel.source_entity_id)
        extra_entity_ids.add(rel.target_entity_id)
        edges.append(_relation_to_dict(rel))

    missing_ids = extra_entity_ids - set(nodes.keys())
    if missing_ids:
        extra_entities = db.query(models.KnowledgeGraphEntity).filter(
            models.KnowledgeGraphEntity.id.in_(missing_ids)
        ).all()
        for entity in extra_entities:
            nodes[entity.id] = _entity_to_dict(entity)

    return success(data={
        "nodes": list(nodes.values())[:max_nodes],  # 防止节点过多炸图
        "edges": edges,
    })


@router.get("/kg/path")
def find_path(
    source_entity_id: int,
    target_entity_id: int,
    max_depth: int = Query(3, ge=1, le=5),
    db: Session = Depends(get_db),
):
    """寻找两个实体之间的路径"""
    # 验证实体存在
    source = db.query(models.KnowledgeGraphEntity).filter(
        models.KnowledgeGraphEntity.id == source_entity_id
    ).first()
    target = db.query(models.KnowledgeGraphEntity).filter(
        models.KnowledgeGraphEntity.id == target_entity_id
    ).first()

    if not source or not target:
        raise HTTPException(status_code=404, detail="实体不存在")

    # 使用NetworkX找最短路径
    try:
        from utils.kg_compute import KnowledgeGraphComputer
        computer = KnowledgeGraphComputer(db)
        path, edges = computer.find_shortest_path(source_entity_id, target_entity_id, max_depth)

        if path:
            node_dicts = []
            for eid in path:
                entity = db.query(models.KnowledgeGraphEntity).filter(
                    models.KnowledgeGraphEntity.id == eid
                ).first()
                if entity:
                    node_dicts.append(_entity_to_dict(entity))

            edge_dicts = [_relation_to_dict(e) for e in edges]

            return success(data={
                "found": True,
                "path": node_dicts,
                "edges": edge_dicts,
            })
        else:
            return success(data={"found": False, "path": None, "edges": None})

    except ImportError:
        # 如果没有图计算工具，返回简单提示
        return success(data={"found": False, "path": None, "edges": None, "message": "需要安装NetworkX"})


# =============== 统计信息 ===============

@router.get("/kg/stats")
def get_kg_stats(db: Session = Depends(get_db)):
    """获取知识图谱统计信息"""
    total_entities = db.query(func.count(models.KnowledgeGraphEntity.id)).scalar() or 0
    total_relations = db.query(func.count(models.KnowledgeGraphRelation.id)).scalar() or 0

    # 按实体类型统计
    entity_type_counts = {}
    entity_type_rows = db.query(
        models.KnowledgeGraphEntity.entity_type,
        func.count(models.KnowledgeGraphEntity.id).label("count")
    ).group_by(models.KnowledgeGraphEntity.entity_type).all()
    for row in entity_type_rows:
        entity_type_counts[row.entity_type] = row.count

    # 按关系类型统计
    relation_type_counts = {}
    relation_type_rows = db.query(
        models.KnowledgeGraphRelation.relation_type,
        func.count(models.KnowledgeGraphRelation.id).label("count")
    ).group_by(models.KnowledgeGraphRelation.relation_type).all()
    for row in relation_type_rows:
        relation_type_counts[row.relation_type] = row.count

    # 平均置信度
    avg_conf_entity = db.query(func.avg(models.KnowledgeGraphEntity.confidence)).scalar() or 0
    avg_conf_rel = db.query(func.avg(models.KnowledgeGraphRelation.confidence)).scalar() or 0
    avg_confidence = (avg_conf_entity + avg_conf_rel) / 2 if total_entities and total_relations else (avg_conf_entity or avg_conf_rel)

    # 最近实体
    recent_entities = db.query(models.KnowledgeGraphEntity).order_by(
        models.KnowledgeGraphEntity.created_at.desc()
    ).limit(10).all()

    return success(data={
        "total_entities": total_entities,
        "total_relations": total_relations,
        "entity_type_counts": entity_type_counts,
        "relation_type_counts": relation_type_counts,
        "avg_confidence": float(avg_confidence),
        "recent_entities": [_entity_to_dict(e) for e in recent_entities],
    })


# =============== 常量信息 ===============

@router.get("/kg/types")
def get_entity_and_relation_types():
    """获取实体类型和关系类型定义"""
    return success(data={
        "entity_types": models.ENTITY_TYPES,
        "relation_types": models.RELATION_TYPES,
    })


# =============== 知识图谱构建 ===============

@router.post("/kg/extract-from-text")
async def extract_from_text(
    request: schemas.ExtractFromTextRequest,
    db: Session = Depends(get_db),
):
    """从自定义文本提取知识图谱"""
    from utils.kg_builder import KnowledgeGraphBuilder

    builder = KnowledgeGraphBuilder(db)
    entities, relations = await builder.extract_from_text(
        text=request.text,
        auto_save=request.auto_save,
    )

    if not entities:
        return error(
            code=422,
            msg="未提取到有效实体，请输入更具体的科学文本（建议不少于20字），或检查LLM配置",
            data={"entities": [], "relations": [], "saved": request.auto_save},
        )

    return success(data={
        "entities": entities,
        "relations": relations,
        "saved": request.auto_save,
        "message": f"提取了 {len(entities)} 个实体和 {len(relations)} 个关系",
    })


@router.post("/kg/extract-from-topic")
async def extract_from_topic(
    request: schemas.ExtractFromTopicRequest,
    db: Session = Depends(get_db),
):
    """按词条调用LLM生成科普文本并提取知识图谱"""
    from utils.kg_builder import KnowledgeGraphBuilder

    builder = KnowledgeGraphBuilder(db)
    entities, relations, generated_text = await builder.extract_from_topic(
        topic=request.topic,
        auto_save=request.auto_save,
    )

    if not entities:
        return error(
            code=422,
            msg="该词条未提取到有效实体，请尝试更具体词条或检查LLM配置",
            data={
                "entities": [],
                "relations": [],
                "saved": request.auto_save,
                "generated_text": generated_text,
            },
        )

    return success(data={
        "entities": entities,
        "relations": relations,
        "saved": request.auto_save,
        "generated_text": generated_text,
        "message": f"词条“{request.topic}”自动抽取完成：{len(entities)} 个实体，{len(relations)} 个关系",
    })


@router.post("/kg/extract-from-document")
async def extract_from_document(
    request: schemas.ExtractFromDocumentRequest,
    db: Session = Depends(get_db),
):
    """从文档提取知识图谱"""
    from utils.kg_builder import KnowledgeGraphBuilder

    builder = KnowledgeGraphBuilder(db)
    entities, relations = await builder.extract_from_document(
        document_id=request.document_id,
        auto_save=request.auto_save,
    )

    return success(data={
        "entities": entities,
        "relations": relations,
        "saved": request.auto_save,
        "message": f"提取了 {len(entities)} 个实体和 {len(relations)} 个关系",
    })


@router.post("/kg/extract-from-wikipedia")
async def extract_from_wikipedia(
    request: schemas.ExtractFromWikipediaRequest,
    db: Session = Depends(get_db),
):
    """从维基百科提取知识图谱"""
    from utils.kg_builder import KnowledgeGraphBuilder

    builder = KnowledgeGraphBuilder(db)
    entities, relations, doc_info = await builder.extract_from_wikipedia(
        title=request.title,
        language=request.language,
        auto_save=request.auto_save,
        doc_type=request.doc_type,
    )

    if not entities:
        return error(
            code=422,
            msg="未从维基页面抽取到实体，请尝试更准确的词条名称或检查网络与LLM配置",
            data={"entities": [], "relations": [], "document_info": doc_info, "saved": request.auto_save},
        )

    return success(data={
        "entities": entities,
        "relations": relations,
        "document_info": doc_info,
        "saved": request.auto_save,
        "message": f"提取了 {len(entities)} 个实体和 {len(relations)} 个关系",
    })


@router.post("/kg/build-from-knowledge-base")
async def build_from_knowledge_base(
    limit: Optional[int] = Query(None, description="处理文档数量限制"),
    start_from: int = Query(0, description="起始文档ID"),
    db: Session = Depends(get_db),
):
    """从整个知识库构建图谱"""
    from utils.kg_builder import KnowledgeGraphBuilder

    builder = KnowledgeGraphBuilder(db)
    result = await builder.build_from_knowledge_base(
        limit=limit,
        start_from=start_from,
    )

    return success(data=result, msg="知识库图谱构建完成")


# =============== 图计算接口 ===============

@router.get("/kg/central-entities")
def get_central_entities(
    top_k: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """获取核心实体（基于PageRank）"""
    try:
        from utils.kg_compute import KnowledgeGraphComputer
        computer = KnowledgeGraphComputer(db)

        if not computer.is_available():
            return error(msg="需要安装NetworkX库")

        entities = computer.find_central_entities(top_k=top_k)
        return success(data={"entities": entities})
    except ImportError:
        return error(msg="需要安装NetworkX库")


@router.get("/kg/communities")
def get_communities(
    db: Session = Depends(get_db),
):
    """获取社区发现结果"""
    try:
        from utils.kg_compute import KnowledgeGraphComputer
        computer = KnowledgeGraphComputer(db)

        if not computer.is_available():
            return error(msg="需要安装NetworkX库")

        communities = computer.find_communities()

        # 获取每个社区的实体信息
        result = []
        for i, comm in enumerate(communities[:20]):  # 限制展示社区数量
            entities = []
            for eid in comm[:10]:  # 每个社区只展示前10个实体
                entity = db.query(models.KnowledgeGraphEntity).filter(
                    models.KnowledgeGraphEntity.id == eid
                ).first()
                if entity:
                    entities.append({
                        "id": entity.id,
                        "name": entity.name,
                        "type": entity.entity_type,
                    })
            result.append({
                "community_id": i,
                "size": len(comm),
                "sample_entities": entities,
            })

        return success(data={"communities": result, "total_communities": len(communities)})
    except ImportError:
        return error(msg="需要安装NetworkX库")
