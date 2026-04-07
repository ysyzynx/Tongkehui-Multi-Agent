from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from models import schemas
from utils.database import get_db
from utils.fact_rag import index_fact_document, search_fact_evidence
from utils.wikipedia_client import (
    search_wikipedia,
    get_wikipedia_page_content,
    search_and_ingest_wikipedia,
)
from utils.serpapi_client import (
    search_google_scholar,
    search_and_ingest_google_scholar,
)
from utils.response import error, success


router = APIRouter(prefix="/fact", tags=["FACT知识库 (RAG)"])


@router.post("/ingest", summary="入库权威FACT文档并自动分块建索引")
def ingest_fact_doc(req: schemas.FactIngestRequest, db: Session = Depends(get_db)):
    try:
        result = index_fact_document(
            db,
            {
                "source_name": req.source_name,
                "source_url": req.source_url,
                "publisher": req.publisher,
                "authority_level": req.authority_level,
                "doc_type": req.doc_type or "FACT",
                "topic_tags": req.topic_tags or [],
                "audience_tags": req.audience_tags or [],
                "content": req.content,
            },
        )
        return success(result, msg="FACT文档入库成功")
    except ValueError as ve:
        return error(code=400, msg=str(ve))
    except Exception as ex:
        return error(code=500, msg=f"入库失败: {str(ex)}")


@router.post("/search", summary="混合检索FACT证据")
def search_fact(req: schemas.FactSearchRequest, db: Session = Depends(get_db)):
    query = (req.query or "").strip()
    if not query:
        return error(code=400, msg="query 不能为空")

    # 支持按 doc_type 筛选（通过查询参数传递）
    # 为保持向后兼容，默认不筛选
    doc_type = None
    # 注意：这里可以扩展为从 req 中获取，当前先保持简单

    items = search_fact_evidence(db, query=query, top_k=req.top_k or 5, doc_type=doc_type)
    return success({"items": items, "count": len(items)}, msg="检索完成")


# ========== 维基百科集成 ==========

@router.post("/wikipedia/search", summary="搜索维基百科（仅搜索，不入库）")
def search_wikipedia_endpoint(req: schemas.WikipediaSearchRequest):
    """
    搜索维基百科页面，返回搜索结果列表
    """
    query = (req.query or "").strip()
    if not query:
        return error(code=400, msg="query 不能为空")

    results = search_wikipedia(
        query=query,
        limit=req.limit or 5,
        language=req.language or "zh"
    )
    return success({"results": results, "count": len(results)}, msg="维基百科搜索完成")


@router.post("/wikipedia/page", summary="获取维基百科单页内容（仅获取，不入库）")
def get_wikipedia_page_endpoint(req: schemas.WikipediaIngestByIdRequest):
    """
    获取维基百科页面完整内容
    - 使用 pageid 或 title 二选一
    """
    if not req.pageid and not req.title:
        return error(code=400, msg="pageid 和 title 必须提供一个")

    page = get_wikipedia_page_content(
        pageid=req.pageid,
        title=req.title,
        language=req.language or "zh"
    )

    if not page:
        return error(code=404, msg="未找到维基百科页面")

    return success(page, msg="获取维基百科页面成功")


@router.post("/wikipedia/ingest", summary="搜索维基百科并自动入库到RAG")
def ingest_wikipedia_endpoint(req: schemas.WikipediaIngestRequest, db: Session = Depends(get_db)):
    """
    搜索维基百科并将结果自动入库到RAG知识库
    - 默认入库到 SCIENCE_FACT（科学审查者库）
    """
    query = (req.query or "").strip()
    if not query:
        return error(code=400, msg="query 不能为空")

    try:
        ingested = search_and_ingest_wikipedia(
            db,
            query=query,
            doc_type=req.doc_type or "SCIENCE_FACT",
            authority_level=req.authority_level or 90,
            limit=req.limit or 3,
            language=req.language or "zh",
            publisher=req.publisher or "维基百科"
        )
        return success(
            {"ingested": ingested, "count": len(ingested)},
            msg=f"成功入库 {len(ingested)} 条维基百科内容"
        )
    except Exception as ex:
        return error(code=500, msg=f"维基百科入库失败: {str(ex)}")


@router.post("/wikipedia/ingest-by-id", summary="指定维基百科页面ID/标题入库")
def ingest_wikipedia_by_id_endpoint(req: schemas.WikipediaIngestByIdRequest, db: Session = Depends(get_db)):
    """
    直接指定维基百科的 pageid 或 title 入库
    """
    from utils.fact_rag import index_fact_document

    if not req.pageid and not req.title:
        return error(code=400, msg="pageid 和 title 必须提供一个")

    # 获取页面内容
    page = get_wikipedia_page_content(
        pageid=req.pageid,
        title=req.title,
        language=req.language or "zh"
    )

    if not page or not page.get("content"):
        return error(code=404, msg="未找到维基百科页面或内容为空")

    # 入库
    try:
        topic_tags = page.get("categories", [])[:8]
        result = index_fact_document(
            db,
            {
                "source_name": f"维基百科: {page.get('title', '')}",
                "source_url": page.get("url"),
                "publisher": req.publisher or "维基百科",
                "authority_level": req.authority_level or 90,
                "doc_type": req.doc_type or "SCIENCE_FACT",
                "topic_tags": topic_tags,
                "audience_tags": ["科普", "科学知识"],
                "content": page.get("content", ""),
            }
        )
        result["wikipedia_title"] = page.get("title")
        result["wikipedia_url"] = page.get("url")
        return success(result, msg="维基百科页面入库成功")
    except ValueError as ve:
        return error(code=400, msg=str(ve))
    except Exception as ex:
        return error(code=500, msg=f"入库失败: {str(ex)}")


# ========== SerpAPI (谷歌学术) 集成 ==========
# 注意：由于免费额度有限，此功能默认不主动使用，主要依靠维基百科

@router.post("/serpapi/search", summary="[默认关闭] 搜索谷歌学术（仅搜索，不入库）")
def search_google_scholar_endpoint(req: schemas.SerpAPISearchRequest):
    """
    搜索谷歌学术（仅用于测试/特殊场景，免费额度有限）
    """
    query = (req.query or "").strip()
    if not query:
        return error(code=400, msg="query 不能为空")

    results = search_google_scholar(
        query=query,
        limit=req.limit or 5,
        language=req.language or "zh-CN"
    )
    return success({"results": results, "count": len(results)}, msg="谷歌学术搜索完成")


@router.post("/serpapi/ingest", summary="[默认关闭] 搜索谷歌学术并自动入库到RAG")
def ingest_google_scholar_endpoint(req: schemas.SerpAPIIngestRequest, db: Session = Depends(get_db)):
    """
    搜索谷歌学术并将结果自动入库到RAG知识库
    注意：免费额度有限，请谨慎使用！
    - 默认入库到 SCIENCE_FACT（科学审查者库）
    """
    query = (req.query or "").strip()
    if not query:
        return error(code=400, msg="query 不能为空")

    try:
        ingested = search_and_ingest_google_scholar(
            db,
            query=query,
            doc_type=req.doc_type or "SCIENCE_FACT",
            authority_level=req.authority_level or 95,
            limit=req.limit or 3,
            publisher=req.publisher or "谷歌学术",
            language=req.language or "zh-CN"
        )
        return success(
            {"ingested": ingested, "count": len(ingested)},
            msg=f"成功入库 {len(ingested)} 条谷歌学术内容"
        )
    except Exception as ex:
        return error(code=500, msg=f"谷歌学术入库失败: {str(ex)}")
