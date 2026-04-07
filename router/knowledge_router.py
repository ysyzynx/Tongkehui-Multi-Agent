"""
知识库管理API路由
提供知识文档的CRUD、检索、统计等功能
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from utils.database import get_db
from models import models, schemas
from utils.fact_rag import index_fact_document, search_fact_evidence, _safe_json_loads, _safe_json_dumps
from utils.response import success, error

router = APIRouter(tags=["Knowledge Base"])


def _document_to_dict(doc: models.KnowledgeDocument, chunk_count: Optional[int] = None) -> Dict[str, Any]:
    """将数据库文档模型转换为字典"""
    return {
        "id": doc.id,
        "source_name": doc.source_name,
        "source_url": doc.source_url,
        "publisher": doc.publisher,
        "author": doc.author,
        "publish_year": doc.publish_year,
        "authority_level": doc.authority_level,
        "doc_type": doc.doc_type,
        "topic_tags": _safe_json_loads(doc.topic_tags, []),
        "audience_tags": _safe_json_loads(doc.audience_tags, []),
        "style_tags": _safe_json_loads(doc.style_tags, []),
        "award_tags": _safe_json_loads(doc.award_tags, []),
        "content": doc.content,
        "chunk_count": chunk_count,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }


def _document_to_list_item_dict(doc: models.KnowledgeDocument, chunk_count: Optional[int] = None) -> Dict[str, Any]:
    """将数据库文档模型转换为列表项字典"""
    return {
        "id": doc.id,
        "source_name": doc.source_name,
        "source_url": doc.source_url,
        "publisher": doc.publisher,
        "author": doc.author,
        "publish_year": doc.publish_year,
        "authority_level": doc.authority_level,
        "doc_type": doc.doc_type,
        "topic_tags": _safe_json_loads(doc.topic_tags, []),
        "audience_tags": _safe_json_loads(doc.audience_tags, []),
        "style_tags": _safe_json_loads(doc.style_tags, []),
        "award_tags": _safe_json_loads(doc.award_tags, []),
        "content_preview": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
        "chunk_count": chunk_count,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }


# =============== Document CRUD ===============

@router.get("/knowledge/documents")
def list_documents(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    doc_type: Optional[str] = Query(None, description="文档类型筛选"),
    topic_tag: Optional[str] = Query(None, description="主题标签筛选"),
    audience_tag: Optional[str] = Query(None, description="受众标签筛选"),
    min_authority: Optional[int] = Query(None, ge=0, le=100, description="最低权威度"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
):
    """
    列出知识库文档（支持分页和筛选）
    """
    query_builder = db.query(models.KnowledgeDocument)

    # 应用筛选条件
    filters = []
    if doc_type:
        filters.append(models.KnowledgeDocument.doc_type == doc_type)
    if min_authority is not None:
        filters.append(models.KnowledgeDocument.authority_level >= min_authority)
    if topic_tag:
        filters.append(models.KnowledgeDocument.topic_tags.contains(topic_tag))
    if audience_tag:
        filters.append(models.KnowledgeDocument.audience_tags.contains(audience_tag))
    if search:
        filters.append(
            or_(
                models.KnowledgeDocument.source_name.contains(search),
                models.KnowledgeDocument.content.contains(search),
            )
        )

    if filters:
        query_builder = query_builder.filter(and_(*filters))

    # 获取总数
    total = query_builder.count()

    # 分页查询
    offset = (page - 1) * page_size
    documents = query_builder.order_by(models.KnowledgeDocument.created_at.desc()).offset(offset).limit(page_size).all()

    # 获取每个文档的分块数量
    doc_ids = [d.id for d in documents]
    chunk_counts = {}
    if doc_ids:
        chunk_query = (
            db.query(
                models.KnowledgeChunk.document_id,
                func.count(models.KnowledgeChunk.id).label("count")
            )
            .filter(models.KnowledgeChunk.document_id.in_(doc_ids))
            .group_by(models.KnowledgeChunk.document_id)
        )
        for row in chunk_query:
            chunk_counts[row.document_id] = row.count

    # 构建响应
    items = [
        _document_to_list_item_dict(doc, chunk_counts.get(doc.id, 0))
        for doc in documents
    ]

    total_pages = (total + page_size - 1) // page_size

    return success(data={
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    })


@router.get("/knowledge/documents/{document_id}")
def get_document(document_id: int, db: Session = Depends(get_db)):
    """
    获取单个文档详情
    """
    doc = db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 获取分块数量
    chunk_count = db.query(func.count(models.KnowledgeChunk.id)).filter(
        models.KnowledgeChunk.document_id == document_id
    ).scalar()

    return success(data=_document_to_dict(doc, chunk_count))


@router.post("/knowledge/documents")
def create_document(
    request: schemas.KnowledgeDocumentCreate,
    db: Session = Depends(get_db),
):
    """
    创建新文档并自动索引
    """
    try:
        # 使用fact_rag中的索引函数
        result = index_fact_document(db, request.model_dump())

        # 获取创建的文档
        doc = db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.id == result["document_id"]).first()

        return success(
            data=_document_to_dict(doc, result["chunk_count"]),
            msg="文档创建成功",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/knowledge/documents/{document_id}")
def update_document(
    document_id: int,
    request: schemas.KnowledgeDocumentUpdate,
    db: Session = Depends(get_db),
):
    """
    更新文档（更新后需要手动重新索引
    """
    doc = db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 更新字段
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ["topic_tags", "audience_tags", "style_tags", "award_tags"]:
            setattr(doc, field, _safe_json_dumps(value))
        else:
            setattr(doc, field, value)

    db.commit()
    db.refresh(doc)

    chunk_count = db.query(func.count(models.KnowledgeChunk.id)).filter(
        models.KnowledgeChunk.document_id == document_id
    ).scalar()

    return success(
        data=_document_to_dict(doc, chunk_count),
        msg="文档更新成功",
    )


@router.delete("/knowledge/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    """
    删除文档及其分块
    """
    doc = db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 删除关联的分块
    db.query(models.KnowledgeChunk).filter(models.KnowledgeChunk.document_id == document_id).delete()

    # 删除文档
    db.delete(doc)
    db.commit()

    return success(
        data={"document_id": document_id},
        msg="文档删除成功",
    )


@router.post("/knowledge/documents/{document_id}/reindex")
def reindex_document(document_id: int, db: Session = Depends(get_db)):
    """
    重新索引文档（删除旧分块并重新创建）
    """
    doc = db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 删除旧分块
    db.query(models.KnowledgeChunk).filter(models.KnowledgeChunk.document_id == document_id).delete()

    # 重新索引
    payload = {
        "source_name": doc.source_name,
        "source_url": doc.source_url,
        "publisher": doc.publisher,
        "author": doc.author,
        "publish_year": doc.publish_year,
        "authority_level": doc.authority_level,
        "doc_type": doc.doc_type,
        "topic_tags": _safe_json_loads(doc.topic_tags, []),
        "audience_tags": _safe_json_loads(doc.audience_tags, []),
        "style_tags": _safe_json_loads(doc.style_tags, []),
        "award_tags": _safe_json_loads(doc.award_tags, []),
        "content": doc.content,
    }

    result = index_fact_document(db, payload)

    return success(data={
        "document_id": result["document_id"],
        "chunk_count": result["chunk_count"],
        "status": "success",
    })


# =============== Search ===============

@router.post("/knowledge/search")
def search_knowledge(
    request: schemas.KnowledgeSearchRequest,
    db: Session = Depends(get_db),
):
    """
    检索知识库（混合检索：向量 + 关键词）
    """
    results = search_fact_evidence(
        db,
        query=request.query,
        top_k=request.top_k,
        doc_type=request.doc_type,
    )

    # 这里可以添加额外的筛选逻辑
    filtered_results = []
    for item in results:
        # 最低权威度筛选
        if request.min_authority_level is not None:
            if item.get("authority_level", 0) < request.min_authority_level:
                continue
        filtered_results.append(item)

    return success(data={
        "query": request.query,
        "results": filtered_results,
        "total": len(filtered_results),
    })


@router.get("/knowledge/documents/{document_id}/chunks")
def get_document_chunks(document_id: int, db: Session = Depends(get_db)):
    """
    获取文档的所有分块
    """
    doc = db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    chunks = db.query(models.KnowledgeChunk).filter(
        models.KnowledgeChunk.document_id == document_id
    ).order_by(models.KnowledgeChunk.chunk_index).all()

    result = []
    for chunk in chunks:
        result.append({
            "id": chunk.id,
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "chunk_text": chunk.chunk_text,
            "keywords": _safe_json_loads(chunk.keywords, []),
            "created_at": chunk.created_at.isoformat() if chunk.created_at else None,
        })

    return success(data=result)


# =============== Batch Import ===============

@router.post("/knowledge/batch-import")
def batch_import_documents(
    request: schemas.KnowledgeBatchImportRequest,
    db: Session = Depends(get_db),
):
    """
    批量导入文档
    """
    success_count = 0
    failed_count = 0
    errors = []
    document_ids = []

    for idx, doc_request in enumerate(request.documents):
        try:
            result = index_fact_document(db, doc_request.model_dump())
            document_ids.append(result["document_id"])
            success_count += 1
        except Exception as e:
            failed_count += 1
            errors.append({
                "index": idx,
                "source_name": doc_request.source_name,
                "error": str(e),
            })

    return success(data={
        "success_count": success_count,
        "failed_count": failed_count,
        "errors": errors if errors else None,
        "document_ids": document_ids if document_ids else None,
    })


# =============== Statistics ===============

@router.get("/knowledge/stats")
def get_knowledge_stats(db: Session = Depends(get_db)):
    """
    获取知识库统计信息
    """
    # 基础统计
    total_documents = db.query(func.count(models.KnowledgeDocument.id)).scalar() or 0
    total_chunks = db.query(func.count(models.KnowledgeChunk.id)).scalar() or 0

    # 平均权威度
    avg_auth = db.query(func.avg(models.KnowledgeDocument.authority_level)).scalar() or 0

    # 按文档类型统计
    doc_type_counts = {}
    doc_type_rows = (
        db.query(
            models.KnowledgeDocument.doc_type,
            func.count(models.KnowledgeDocument.id).label("count")
        )
        .group_by(models.KnowledgeDocument.doc_type)
    )
    for row in doc_type_rows:
        doc_type_counts[row.doc_type] = row.count

    # 最近文档
    recent_docs = (
        db.query(models.KnowledgeDocument)
        .order_by(models.KnowledgeDocument.created_at.desc())
        .limit(5)
        .all()
    )

    recent_items = [_document_to_list_item_dict(doc) for doc in recent_docs]

    return success(data={
        "total_documents": total_documents,
        "total_chunks": total_chunks,
        "doc_type_counts": doc_type_counts,
        "topic_tag_counts": {},
        "audience_tag_counts": {},
        "avg_authority_level": float(avg_auth),
        "recent_documents": recent_items,
    })


# =============== Content Collector ===============

@router.get("/knowledge/collector/sites")
def list_supported_sites():
    """
    列出支持的科普网站
    """
    sites = [
        {
            "id": "kepu_net_cn",
            "name": "中国科普博览",
            "url": "https://www.kepu.net.cn",
            "description": "中科院主办的科普网站",
            "authority_level": 90,
        },
        {
            "id": "sciencenet_cn",
            "name": "科学网博客",
            "url": "https://blog.sciencenet.cn",
            "description": "科研工作者社区",
            "authority_level": 85,
        },
        {
            "id": "guokr_com",
            "name": "果壳网",
            "url": "https://www.guokr.com",
            "description": "青年向趣味科普",
            "authority_level": 85,
        },
        {
            "id": "kepu_gov_cn",
            "name": "科普中国",
            "url": "https://www.kepu.gov.cn",
            "description": "官方科普平台",
            "authority_level": 95,
        },
        {
            "id": "cas_voice",
            "name": "中科院之声",
            "url": "https://www.cas.cn/voice",
            "description": "中国科学院官方",
            "authority_level": 95,
        },
    ]
    return success(data={"sites": sites})


@router.post("/knowledge/collector/from-site")
def collect_from_site(
    request: schemas.CollectFromSiteRequest,
    db: Session = Depends(get_db),
):
    """
    从指定网站采集内容
    """
    from utils.science_collector import (
        get_science_collector,
        ingest_collected_articles,
    )

    collector = get_science_collector()

    try:
        # 采集文章
        articles = collector.collect_from_site(
            site_name=request.site_name,
            limit=request.limit,
        )

        if not articles:
            return success(data={
                "site_name": request.site_name,
                "collected_count": 0,
                "articles": [],
                "message": "未采集到文章",
            })

        # 构建预览数据
        article_previews = []
        for art in articles:
            preview = {
                "source_name": art.source_name,
                "source_url": art.source_url,
                "title": art.title,
                "author": art.author,
                "publisher": art.publisher,
                "publish_date": art.publish_date,
                "content_preview": art.content[:200] + "..." if art.content and len(art.content) > 200 else art.content,
                "topic_tags": art.topic_tags,
                "authority_level": art.authority_level,
            }
            article_previews.append(preview)

        result = {
            "site_name": request.site_name,
            "collected_count": len(articles),
            "articles": article_previews,
        }

        # 如果自动入库
        if request.auto_ingest:
            ingest_results = ingest_collected_articles(
                db,
                articles,
                doc_type=request.doc_type,
            )
            result["ingested_count"] = len(ingest_results)
            result["ingest_results"] = ingest_results

        return success(data=result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"采集失败: {str(e)}")


@router.post("/knowledge/collector/all-sites")
def collect_all_sites(
    request: schemas.CollectAllSitesRequest,
    db: Session = Depends(get_db),
):
    """
    从所有网站采集内容
    """
    from utils.science_collector import (
        get_science_collector,
        ingest_collected_articles,
    )

    collector = get_science_collector()

    try:
        # 从所有网站采集
        articles = collector.collect_all_sites(per_site_limit=request.per_site_limit)

        if not articles:
            return success(data={
                "total_collected": 0,
                "per_site_results": {},
                "message": "未采集到任何文章",
            })

        # 按网站分组
        per_site_results = {}
        site_names = ["kepu_net_cn", "sciencenet_cn", "guokr_com", "kepu_gov_cn", "cas_voice"]

        for site_name in site_names:
            site_articles = [a for a in articles if site_name in (a.source_url or "") or site_name in (a.publisher or "")]
            if site_articles:
                previews = []
                for art in site_articles:
                    previews.append({
                        "source_name": art.source_name,
                        "source_url": art.source_url,
                        "title": art.title,
                        "author": art.author,
                        "publisher": art.publisher,
                        "publish_date": art.publish_date,
                        "content_preview": art.content[:200] + "..." if art.content and len(art.content) > 200 else art.content,
                        "topic_tags": art.topic_tags,
                        "authority_level": art.authority_level,
                    })
                per_site_results[site_name] = {
                    "site_name": site_name,
                    "collected_count": len(site_articles),
                    "articles": previews,
                }

        result = {
            "total_collected": len(articles),
            "per_site_results": per_site_results,
        }

        # 如果自动入库
        if request.auto_ingest:
            ingest_results = ingest_collected_articles(
                db,
                articles,
                doc_type=request.doc_type,
            )
            result["total_ingested"] = len(ingest_results)

        return success(data=result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"采集失败: {str(e)}")


# =============== RAG Pre-Retrieval ===============

@router.post("/knowledge/preretrieve")
def preretrieve_knowledge(
    request: schemas.KnowledgeSearchRequest,
    db: Session = Depends(get_db),
):
    """
    RAG预检索：在创作前预览相关参考材料
    与search接口类似，但返回更详细的信息供前端展示
    """
    try:
        results = search_fact_evidence(
            db,
            query=request.query,
            top_k=request.top_k,
            doc_type=request.doc_type,
        )

        # 过滤和增强结果
        enriched_results = []
        for item in results:
            # 最低权威度筛选
            if request.min_authority_level is not None:
                if item.get("authority_level", 0) < request.min_authority_level:
                    continue

            # 增强信息，获取完整文档（如果需要）
            enriched_item = {
                **item,
                "selected": True,  # 默认选中
            }
            enriched_results.append(enriched_item)

        return success(data={
            "query": request.query,
            "results": enriched_results,
            "total": len(enriched_results),
        })
    except Exception as e:
        print(f"[preretrieve_knowledge] 错误: {e}")
        import traceback
        traceback.print_exc()
        return success(data={
            "query": request.query,
            "results": [],
            "total": 0,
        })


# =============== Topic Search & Collect ===============

@router.post("/knowledge/search-topic")
def search_topic_and_collect(
    request: schemas.TopicSearchRequest,
    db: Session = Depends(get_db),
):
    """
    按主题搜索科普网站并可选地自动入库到知识库

    功能：
    1. 根据用户输入的主题在多个科普网站搜索相关文章
    2. 可选择是否自动将搜索结果入库到个人知识库
    3. 返回搜索结果供用户预览和选择
    """
    from utils.science_collector import (
        get_science_collector,
        ingest_collected_articles,
    )

    topic = request.topic.strip()
    if len(topic) < 2:
        raise HTTPException(status_code=400, detail="主题至少需要2个字符")

    collector = get_science_collector()

    try:
        # 1. 按主题搜索文章
        articles = collector.search_by_topic(
            topic=topic,
            sites=request.sites,
            limit_per_site=request.limit_per_site,
        )

        if not articles:
            return success(data={
                "topic": topic,
                "total_found": 0,
                "results": [],
                "ingested_count": 0,
                "sites_searched": request.sites or list(collector.SEARCH_SITES.keys()),
            })

        # 2. 构建预览结果
        results = []
        for art in articles:
            results.append({
                "source_name": art.source_name,
                "source_url": art.source_url,
                "title": art.title,
                "author": art.author,
                "publisher": art.publisher,
                "content_preview": art.content[:200] + "..." if art.content and len(art.content) > 200 else art.content,
                "topic_tags": art.topic_tags,
                "authority_level": art.authority_level,
                "document_id": None,  # 稍后填充
            })

        ingested_count = 0
        ingest_results = []

        # 3. 如果自动入库
        if request.auto_ingest:
            ingest_results = ingest_collected_articles(
                db,
                articles,
                doc_type=request.doc_type,
            )
            ingested_count = len(ingest_results)

            # 将入库后的文档ID填充到结果中
            if ingest_results:
                # 建立标题到文档ID的映射
                title_to_id = {
                    r.get("article_title", ""): r.get("document_id")
                    for r in ingest_results
                }
                # 填充document_id
                for res in results:
                    res["document_id"] = title_to_id.get(res.get("title", ""))

        return success(data={
            "topic": topic,
            "total_found": len(results),
            "results": results,
            "ingested_count": ingested_count,
            "sites_searched": request.sites or list(collector.SEARCH_SITES.keys()),
        })

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")
