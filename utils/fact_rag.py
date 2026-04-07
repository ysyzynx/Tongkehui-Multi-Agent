import json
import math
import re
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from models import models
from utils.llm_client import llm_client


STOPWORDS = {
    "我们", "你们", "他们", "自己", "这个", "那个", "这些", "那些", "一种", "一个", "一些",
    "因为", "所以", "如果", "但是", "然后", "于是", "已经", "可以", "需要", "通过", "进行",
    "并且", "以及", "或者", "其中", "为了", "这里", "那里", "大家", "孩子", "老师", "故事",
    "科学", "科普", "文章", "内容", "问题", "建议", "相关", "部分",
}


def _safe_json_loads(text: str, fallback: Any):
    try:
        return json.loads(text) if text else fallback
    except Exception:
        return fallback


def _safe_json_dumps(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return "[]"


def split_text(content: str, max_chars: int = 420, overlap: int = 60) -> List[str]:
    text = (content or "").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    chunks: List[str] = []
    for p in paragraphs:
        if len(p) <= max_chars:
            chunks.append(p)
            continue

        start = 0
        while start < len(p):
            end = min(len(p), start + max_chars)
            chunks.append(p[start:end].strip())
            if end >= len(p):
                break
            start = max(0, end - overlap)

    return [c for c in chunks if c]


def extract_keywords(text: str, top_k: int = 12) -> List[str]:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,10}", text or "")
    freq: Dict[str, int] = {}
    for token in tokens:
        t = token.strip()
        if not t or t in STOPWORDS:
            continue
        freq[t] = freq.get(t, 0) + 1

    ranked = sorted(freq.items(), key=lambda x: (-x[1], -len(x[0]), x[0]))
    return [item[0] for item in ranked[:top_k]]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def index_fact_document(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    source_name = str(payload.get("source_name") or "").strip()
    content = str(payload.get("content") or "").strip()
    if not source_name:
        raise ValueError("source_name 不能为空")
    if not content:
        raise ValueError("content 不能为空")

    authority_level = int(payload.get("authority_level") or 80)
    authority_level = max(0, min(100, authority_level))

    # 支持的文档类型：
    # - CREATOR_STYLE: 创作者知识库（科普获奖作品等）
    # - SCIENCE_FACT: 科学审查者知识库（教材、权威资料等）
    # - FACT: 通用事实知识库（兼容旧数据）
    doc_type = str(payload.get("doc_type") or "FACT").strip().upper()
    valid_doc_types = ["CREATOR_STYLE", "SCIENCE_FACT", "FACT"]
    if doc_type not in valid_doc_types:
        doc_type = "FACT"

    document = models.KnowledgeDocument(
        source_name=source_name,
        source_url=str(payload.get("source_url") or "").strip() or None,
        publisher=str(payload.get("publisher") or "").strip() or None,
        author=str(payload.get("author") or "").strip() or None,
        publish_year=int(payload.get("publish_year")) if payload.get("publish_year") else None,
        authority_level=authority_level,
        doc_type=doc_type,
        topic_tags=_safe_json_dumps(payload.get("topic_tags") or []),
        audience_tags=_safe_json_dumps(payload.get("audience_tags") or []),
        style_tags=_safe_json_dumps(payload.get("style_tags") or []),
        award_tags=_safe_json_dumps(payload.get("award_tags") or []),
        content=content,
    )
    db.add(document)
    db.flush()

    chunks = split_text(content)
    created_chunks = 0
    for idx, chunk in enumerate(chunks):
        keywords = extract_keywords(chunk)
        embedding = llm_client.generate_embedding(chunk)
        chunk_row = models.KnowledgeChunk(
            document_id=document.id,
            chunk_index=idx,
            chunk_text=chunk,
            keywords=_safe_json_dumps(keywords),
            embedding=_safe_json_dumps(embedding),
        )
        db.add(chunk_row)
        created_chunks += 1

    db.commit()
    db.refresh(document)

    return {
        "document_id": document.id,
        "source_name": document.source_name,
        "chunk_count": created_chunks,
        "authority_level": document.authority_level,
    }


def search_fact_evidence(db: Session, query: str, top_k: int = 5, doc_type: str = None) -> List[Dict[str, Any]]:
    """
    检索知识库证据
    :param db: 数据库会话
    :param query: 查询文本
    :param top_k: 返回结果数量
    :param doc_type: 文档类型筛选（CREATOR_STYLE/SCIENCE_FACT/FACT/None），None表示不筛选
    """
    try:
        q = (query or "").strip()
        if not q:
            return []

        query_keywords = set(extract_keywords(q, top_k=18))
        query_embedding = llm_client.generate_embedding(q)

        # 构建查询
        query_builder = (
            db.query(models.KnowledgeChunk, models.KnowledgeDocument)
            .join(models.KnowledgeDocument, models.KnowledgeChunk.document_id == models.KnowledgeDocument.id)
        )

        # 如果指定了 doc_type，则筛选
        if doc_type:
            query_builder = query_builder.filter(models.KnowledgeDocument.doc_type == doc_type)

        rows = query_builder.all()

        scored: List[Dict[str, Any]] = []
        for chunk, doc in rows:
            chunk_keywords = set(_safe_json_loads(chunk.keywords, []))
            if query_keywords and chunk_keywords:
                overlap = len(query_keywords.intersection(chunk_keywords)) / max(1, len(query_keywords))
            else:
                overlap = 0.0

            chunk_embedding = _safe_json_loads(chunk.embedding, [])
            vector_score = cosine_similarity(query_embedding, chunk_embedding)

            authority_boost = max(0.0, min(1.0, (doc.authority_level or 0) / 100.0))
            final_score = 0.45 * overlap + 0.45 * vector_score + 0.10 * authority_boost

            if final_score <= 0:
                continue

            scored.append({
                "evidence_id": f"doc{doc.id}-chunk{chunk.chunk_index}",
                "source_name": doc.source_name,
                "source_url": doc.source_url,
                "publisher": doc.publisher,
                "authority_level": doc.authority_level or 0,
                "score": round(float(final_score), 4),
                "snippet": chunk.chunk_text[:240],
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[: max(1, min(int(top_k or 5), 12))]
    except Exception as e:
        print(f"[search_fact_evidence] 错误: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_fact_evidence_by_ids(db: Session, doc_ids: List[int], top_k_per_doc: int = 2) -> List[Dict[str, Any]]:
    """
    根据指定的文档ID列表获取证据
    :param db: 数据库会话
    :param doc_ids: 文档ID列表
    :param top_k_per_doc: 每个文档返回的最大分块数
    """
    if not doc_ids:
        return []

    # 查询指定文档的所有分块
    query_builder = (
        db.query(models.KnowledgeChunk, models.KnowledgeDocument)
        .join(models.KnowledgeDocument, models.KnowledgeChunk.document_id == models.KnowledgeDocument.id)
        .filter(models.KnowledgeDocument.id.in_(doc_ids))
    )

    rows = query_builder.all()

    # 按文档ID分组
    doc_chunks: Dict[int, List[Dict[str, Any]]] = {}
    for chunk, doc in rows:
        if doc.id not in doc_chunks:
            doc_chunks[doc.id] = []
        doc_chunks[doc.id].append({
            "evidence_id": f"doc{doc.id}-chunk{chunk.chunk_index}",
            "source_name": doc.source_name,
            "source_url": doc.source_url,
            "publisher": doc.publisher,
            "authority_level": doc.authority_level or 0,
            "score": 1.0,  # 固定高分因为是用户选中的
            "snippet": chunk.chunk_text[:240],
        })

    # 从每个文档取前top_k_per_doc个分块
    results = []
    for doc_id in doc_ids:
        if doc_id in doc_chunks:
            results.extend(doc_chunks[doc_id][:top_k_per_doc])

    return results
