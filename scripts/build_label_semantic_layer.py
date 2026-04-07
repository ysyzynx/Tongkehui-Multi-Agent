#!/usr/bin/env python3
"""
Phase-2: 外部语义知识层（标签增强）构建脚本

任务二交付：
1) 标签相关子图抽取（标签节点、同义词节点、关系边）
2) 构建标签关系矩阵（共现矩阵 + 条件概率矩阵）
3) 输出每个标签的增强向量（工程可行版：图统计特征 + 嵌入聚合）
4) 生成可视化校验文件（HTML）

设计原则：
- 只读数据库
- 不修改现有业务路由与在线流程
- 尽量复用现有能力：config.label_taxonomy / utils.kg_builder / utils.fact_rag / utils.llm_client
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import or_  # noqa: E402

from config.label_taxonomy import LabelDef, list_labels, load_label_taxonomy  # noqa: E402
from models import models  # noqa: E402
from utils.database import SessionLocal  # noqa: E402
from utils.fact_rag import cosine_similarity, search_fact_evidence  # noqa: E402
from utils.kg_builder import find_entity_by_name, normalize_entity_name  # noqa: E402
from utils.llm_client import llm_client  # noqa: E402


@dataclass
class LabelGraphBundle:
    label_id: str
    label_name: str
    seed_terms: List[str]
    entity_ids: Set[int]
    entity_names: List[str]
    neighbor_entity_ids: Set[int]
    relation_edges: List[Dict[str, Any]]
    evidence_items: List[Dict[str, Any]]
    entity_type_counter: Dict[str, int]


def _safe_json_loads(text: str, fallback: Any) -> Any:
    try:
        return json.loads(text) if text else fallback
    except Exception:
        return fallback


def _safe_json_dumps(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        return "{}"


def _get_attr(instance: Any, name: str, default: Any = None) -> Any:
    value = getattr(instance, name, default)
    return default if value is None else value


def _mean_vector(vectors: List[List[float]]) -> List[float]:
    valid = [v for v in vectors if isinstance(v, list) and v]
    if not valid:
        return []

    dim = len(valid[0])
    same_dim = [v for v in valid if len(v) == dim]
    if not same_dim:
        return []

    sums = [0.0] * dim
    for v in same_dim:
        for i, x in enumerate(v):
            sums[i] += float(x)

    n = float(len(same_dim))
    return [x / n for x in sums]


def _weighted_merge(vectors: List[List[float]], weights: List[float]) -> List[float]:
    pairs = [(v, w) for v, w in zip(vectors, weights) if isinstance(v, list) and v and w > 0]
    if not pairs:
        return []

    dim = len(pairs[0][0])
    pairs = [(v, w) for v, w in pairs if len(v) == dim]
    if not pairs:
        return []

    denom = sum(w for _, w in pairs)
    if denom <= 0:
        return []

    sums = [0.0] * dim
    for vec, weight in pairs:
        for i, x in enumerate(vec):
            sums[i] += float(x) * weight

    return [x / denom for x in sums]


def _vector_norm(v: List[float]) -> float:
    return math.sqrt(sum(x * x for x in v)) if v else 0.0


def _tokenize_cn_text(text: str) -> List[str]:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,8}", str(text or ""))
    return [t.strip() for t in tokens if t and len(t.strip()) >= 2]


def _hash_token_vector(tokens: List[str], dim: int = 32) -> List[float]:
    if dim <= 0:
        return []
    vec = [0.0 for _ in range(dim)]
    if not tokens:
        return vec

    for tok in tokens:
        idx = abs(hash(tok)) % dim
        vec[idx] += 1.0

    norm = _vector_norm(vec)
    if norm <= 0:
        return vec
    return [x / norm for x in vec]


def _entity_text(entity: models.KnowledgeGraphEntity) -> str:
    parts = [str(_get_attr(entity, "name", "") or "").strip(), str(_get_attr(entity, "description", "") or "").strip()]
    aliases = _safe_json_loads(str(_get_attr(entity, "aliases", "") or ""), [])
    if isinstance(aliases, list):
        parts.extend(str(x).strip() for x in aliases if str(x).strip())
    return " ".join(p for p in parts if p)


def _label_text(label: LabelDef) -> str:
    terms = [label.name, label.definition]
    terms.extend(label.aliases)
    terms.extend(label.positive_hints)
    return " ".join(str(x).strip() for x in terms if str(x).strip())


def _collect_label_seed_terms(label: LabelDef) -> List[str]:
    terms: List[str] = []
    for item in [label.name, *label.aliases, *label.positive_hints]:
        term = normalize_entity_name(str(item or ""))
        if term and term not in terms:
            terms.append(term)
    return terms


def _fetch_all_entities(db) -> List[models.KnowledgeGraphEntity]:
    return db.query(models.KnowledgeGraphEntity).all()


def _keyword_entity_recall(
    label: LabelDef,
    entities: List[models.KnowledgeGraphEntity],
    limit: int = 8,
) -> List[int]:
    label_tokens = set(_tokenize_cn_text(_label_text(label)))
    if not label_tokens:
        return []

    scored: List[Tuple[int, float]] = []
    for e in entities:
        text = _entity_text(e)
        e_tokens = set(_tokenize_cn_text(text))
        if not e_tokens:
            continue
        inter = label_tokens.intersection(e_tokens)
        if not inter:
            continue
        score = float(len(inter)) / float(len(label_tokens))
        if score > 0:
            scored.append((int(_get_attr(e, "id", 0)), score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [eid for eid, _ in scored[: max(1, limit)]]


def _fetch_entity_embeddings(db) -> Dict[int, List[float]]:
    rows = db.query(models.KnowledgeGraphEntityEmbedding).all()
    result: Dict[int, List[float]] = {}
    for row in rows:
        emb = _safe_json_loads(row.embedding, [])
        if isinstance(emb, list) and emb:
            result[int(row.entity_id)] = [float(x) for x in emb]
    return result


def _pick_semantic_entities(
    label_embedding: List[float],
    entity_embeddings: Dict[int, List[float]],
    threshold: float,
    top_k: int,
) -> List[int]:
    if not label_embedding:
        return []

    scored: List[Tuple[int, float]] = []
    for eid, emb in entity_embeddings.items():
        score = cosine_similarity(label_embedding, emb)
        if score >= threshold:
            scored.append((eid, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [eid for eid, _ in scored[: max(1, top_k)]]


def _expand_neighbors(db, seed_entity_ids: Set[int]) -> Tuple[Set[int], List[Dict[str, Any]]]:
    if not seed_entity_ids:
        return set(), []

    edges: List[Dict[str, Any]] = []
    neighbor_ids: Set[int] = set()

    relations = db.query(models.KnowledgeGraphRelation).filter(
        or_(
            models.KnowledgeGraphRelation.source_entity_id.in_(list(seed_entity_ids)),
            models.KnowledgeGraphRelation.target_entity_id.in_(list(seed_entity_ids)),
        )
    ).all()

    for rel in relations:
        src = int(rel.source_entity_id)
        tgt = int(rel.target_entity_id)
        neighbor_ids.add(src)
        neighbor_ids.add(tgt)
        edges.append(
            {
                "id": int(rel.id),
                "source_entity_id": src,
                "target_entity_id": tgt,
                "relation_type": str(rel.relation_type or "RELATED_TO"),
                "confidence": float(rel.confidence or 0.0),
            }
        )

    return neighbor_ids, edges


def _collect_entity_type_counter(db, entity_ids: Set[int]) -> Dict[str, int]:
    counter: Dict[str, int] = {}
    if not entity_ids:
        return counter

    entities = db.query(models.KnowledgeGraphEntity).filter(
        models.KnowledgeGraphEntity.id.in_(list(entity_ids))
    ).all()
    for e in entities:
        t = str(e.entity_type or "CONCEPT")
        counter[t] = counter.get(t, 0) + 1
    return counter


def build_label_bundle(
    db,
    label: LabelDef,
    all_entities: List[models.KnowledgeGraphEntity],
    entity_embeddings: Dict[int, List[float]],
    semantic_top_k: int,
    semantic_threshold: float,
    evidence_top_k: int,
) -> LabelGraphBundle:
    seeds = _collect_label_seed_terms(label)

    matched_entity_ids: Set[int] = set()
    matched_entity_names: List[str] = []

    # 1) 复用 kg_builder 的名称查找能力（精确/模糊/别名）
    for term in seeds:
        entity = find_entity_by_name(db, term)
        if entity is not None:
            eid = int(_get_attr(entity, "id", 0))
            if eid not in matched_entity_ids:
                matched_entity_ids.add(eid)
                matched_entity_names.append(str(_get_attr(entity, "name", "")))

    # 2) 语义补全：label embedding 对齐 entity embedding
    label_embedding = llm_client.generate_embedding(_label_text(label))
    semantic_ids = _pick_semantic_entities(
        label_embedding=label_embedding,
        entity_embeddings=entity_embeddings,
        threshold=semantic_threshold,
        top_k=semantic_top_k,
    )
    matched_entity_ids.update(semantic_ids)

    # 2.1) 关键词召回兜底：当标签抽象且 embedding 不可用时仍可召回局部实体。
    if len(matched_entity_ids) < 2:
        keyword_ids = _keyword_entity_recall(label=label, entities=all_entities, limit=max(3, semantic_top_k))
        matched_entity_ids.update(keyword_ids)

    if semantic_ids:
        semantic_entities = db.query(models.KnowledgeGraphEntity).filter(
            models.KnowledgeGraphEntity.id.in_(semantic_ids)
        ).all()
        for e in semantic_entities:
            n = str(e.name)
            if n and n not in matched_entity_names:
                matched_entity_names.append(n)

    # 3) 扩展邻域关系边
    neighbor_ids, relation_edges = _expand_neighbors(db, matched_entity_ids)

    # 4) 复用 fact_rag 向量检索做语义证据补全
    evidence_items = search_fact_evidence(
        db=db,
        query=_label_text(label),
        top_k=evidence_top_k,
        doc_type="",
    )

    # 5) 统计实体类型分布
    type_counter = _collect_entity_type_counter(db, neighbor_ids or matched_entity_ids)

    return LabelGraphBundle(
        label_id=label.id,
        label_name=label.name,
        seed_terms=seeds,
        entity_ids=matched_entity_ids,
        entity_names=sorted(matched_entity_names),
        neighbor_entity_ids=neighbor_ids,
        relation_edges=relation_edges,
        evidence_items=evidence_items if isinstance(evidence_items, list) else [],
        entity_type_counter=type_counter,
    )


def _build_engineering_features(bundle: LabelGraphBundle, all_entity_types: List[str]) -> Dict[str, float]:
    node_count = float(len(bundle.neighbor_entity_ids or bundle.entity_ids))
    edge_count = float(len(bundle.relation_edges))
    seed_hit_count = float(len(bundle.entity_ids))
    evidence_count = float(len(bundle.evidence_items))

    density = 0.0
    if node_count > 1:
        density = edge_count / (node_count * (node_count - 1.0))

    avg_edge_conf = 0.0
    if bundle.relation_edges:
        avg_edge_conf = sum(float(x.get("confidence") or 0.0) for x in bundle.relation_edges) / len(bundle.relation_edges)

    features: Dict[str, float] = {
        "node_count": node_count,
        "edge_count": edge_count,
        "density": density,
        "seed_entity_count": seed_hit_count,
        "evidence_count": evidence_count,
        "avg_edge_confidence": avg_edge_conf,
    }

    total_type = sum(bundle.entity_type_counter.values())
    for t in all_entity_types:
        k = f"entity_type_ratio::{t}"
        if total_type <= 0:
            features[k] = 0.0
        else:
            features[k] = float(bundle.entity_type_counter.get(t, 0)) / float(total_type)

    return features


def _aggregate_label_semantic_embedding(
    db,
    label: LabelDef,
    bundle: LabelGraphBundle,
    entity_embeddings: Dict[int, List[float]],
) -> Dict[str, Any]:
    label_emb = llm_client.generate_embedding(_label_text(label))

    entity_vecs: List[List[float]] = []
    if bundle.entity_ids:
        entities = db.query(models.KnowledgeGraphEntity).filter(
            models.KnowledgeGraphEntity.id.in_(list(bundle.entity_ids))
        ).all()
        for e in entities:
            eid = int(e.id)
            if eid in entity_embeddings:
                entity_vecs.append(entity_embeddings[eid])
            else:
                fallback = llm_client.generate_embedding(_entity_text(e))
                if fallback:
                    entity_vecs.append(fallback)

    evidence_vecs: List[List[float]] = []
    for ev in bundle.evidence_items:
        snippet = str(ev.get("snippet") or "").strip()
        if snippet:
            emb = llm_client.generate_embedding(snippet)
            if emb:
                evidence_vecs.append(emb)

    entity_mean = _mean_vector(entity_vecs)
    evidence_mean = _mean_vector(evidence_vecs)

    # embedding 不可用时的语义兜底向量（哈希词向量）。
    fallback_tokens: List[str] = []
    fallback_tokens.extend(_tokenize_cn_text(_label_text(label)))
    for name in bundle.entity_names:
        fallback_tokens.extend(_tokenize_cn_text(name))
    for ev in bundle.evidence_items:
        fallback_tokens.extend(_tokenize_cn_text(str(ev.get("snippet") or "")))
    hash_semantic = _hash_token_vector(fallback_tokens, dim=32)

    merged = _weighted_merge(
        vectors=[label_emb, entity_mean, evidence_mean, hash_semantic],
        weights=[0.45, 0.30, 0.10, 0.15],
    )

    if not merged and hash_semantic:
        merged = hash_semantic

    return {
        "label_embedding_dim": len(label_emb),
        "entity_embedding_dim": len(entity_mean),
        "evidence_embedding_dim": len(evidence_mean),
        "enhanced_embedding_dim": len(merged),
        "enhanced_embedding": merged,
        "hash_semantic_dim": len(hash_semantic),
        "embedding_norm": _vector_norm(merged),
    }


def build_relation_matrices(
    label_ids: List[str],
    bundles: Dict[str, LabelGraphBundle],
    labels_by_id: Dict[str, LabelDef],
) -> Dict[str, Any]:
    n = len(label_ids)

    # 共现矩阵：融合三种信号
    # 1) 实体集合交集
    # 2) 证据源交集
    # 3) 标签/证据文本词项交集
    cooccur: List[List[float]] = [[0.0 for _ in range(n)] for _ in range(n)]

    entity_sets: Dict[str, Set[int]] = {}
    source_sets: Dict[str, Set[str]] = {}
    token_sets: Dict[str, Set[str]] = {}
    hash_vecs: Dict[str, List[float]] = {}
    for lid in label_ids:
        b = bundles[lid]
        related = set(b.entity_ids) | set(b.neighbor_entity_ids)
        entity_sets[lid] = related

        srcs: Set[str] = set()
        for ev in b.evidence_items:
            src = str(ev.get("source_name") or "").strip()
            if src:
                srcs.add(src)
        source_sets[lid] = srcs

        toks: Set[str] = set(_tokenize_cn_text(" ".join(b.seed_terms)))
        for ev in b.evidence_items:
            toks.update(_tokenize_cn_text(str(ev.get("snippet") or "")))
        token_sets[lid] = toks

        lb = labels_by_id.get(lid)
        base_text = _label_text(lb) if lb is not None else " ".join(b.seed_terms)
        hash_vecs[lid] = _hash_token_vector(_tokenize_cn_text(base_text), dim=32)

    for i, li in enumerate(label_ids):
        for j, lj in enumerate(label_ids):
            if i == j:
                cooccur[i][j] = float(len(entity_sets[li])) + float(len(source_sets[li]))
                continue
            inter_entity = entity_sets[li].intersection(entity_sets[lj])
            inter_source = source_sets[li].intersection(source_sets[lj])
            inter_token = token_sets[li].intersection(token_sets[lj])

            score = (
                1.0 * float(len(inter_entity))
                + 0.8 * float(len(inter_source))
                + 0.2 * float(len(inter_token))
            )

            # 稀疏场景兜底：使用标签文本哈希向量相似度提供弱连接信号。
            sim = cosine_similarity(hash_vecs.get(li, []), hash_vecs.get(lj, []))
            score += 0.5 * max(0.0, sim)

            cooccur[i][j] = score

    # 条件概率矩阵：P(j|i) = cooccur(i,j) / sum_k cooccur(i,k)
    conditional: List[List[float]] = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        row_sum = sum(cooccur[i])
        if row_sum <= 0:
            continue
        for j in range(n):
            conditional[i][j] = cooccur[i][j] / row_sum

    # 邻接关系（按条件概率取每个标签 top 邻居）
    adjacency: Dict[str, List[Dict[str, Any]]] = {}
    for i, li in enumerate(label_ids):
        pairs: List[Tuple[int, float]] = []
        for j, _ in enumerate(label_ids):
            if i == j:
                continue
            p = conditional[i][j]
            if p > 0:
                pairs.append((j, p))
        pairs.sort(key=lambda x: x[1], reverse=True)

        adjacency[li] = [
            {
                "neighbor_label_id": label_ids[j],
                "conditional_probability": round(float(p), 6),
                "cooccur_score": round(float(cooccur[i][j]), 6),
            }
            for j, p in pairs[:10]
        ]

    return {
        "label_ids": label_ids,
        "cooccurrence_matrix": cooccur,
        "conditional_probability_matrix": conditional,
        "adjacency": adjacency,
    }


def _write_csv_matrix(path: Path, label_ids: List[str], matrix: List[List[float]]) -> None:
    lines: List[str] = []
    header = ["label_id", *label_ids]
    lines.append(",".join(header))
    for i, lid in enumerate(label_ids):
        row = [lid, *[f"{float(x):.6f}" for x in matrix[i]]]
        lines.append(",".join(row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_preview_html(
    output_file: Path,
    labels: Dict[str, LabelDef],
    bundles: Dict[str, LabelGraphBundle],
    matrices: Dict[str, Any],
    preview_limit: int,
) -> None:
    label_ids: List[str] = matrices["label_ids"]
    conditional: List[List[float]] = matrices["conditional_probability_matrix"]

    pairs: List[Tuple[str, str, float]] = []
    for i, li in enumerate(label_ids):
        for j, lj in enumerate(label_ids):
            if i >= j:
                continue
            # 对称展示强度，取 P(j|i)+P(i|j)
            score = float(conditional[i][j]) + float(conditional[j][i])
            if score > 0:
                pairs.append((li, lj, score))
    pairs.sort(key=lambda x: x[2], reverse=True)
    pairs = pairs[: max(10, preview_limit)]

    rows = []
    for li, lj, score in pairs:
        left = labels[li].name if li in labels else li
        right = labels[lj].name if lj in labels else lj
        rows.append(f"<tr><td>{li}</td><td>{left}</td><td>{lj}</td><td>{right}</td><td>{score:.4f}</td></tr>")

    detail_rows = []
    for lid in label_ids[:preview_limit]:
        lb = labels.get(lid)
        bundle = bundles[lid]
        detail_rows.append(
            "<tr>"
            f"<td>{lid}</td>"
            f"<td>{(lb.name if lb else lid)}</td>"
            f"<td>{len(bundle.entity_ids)}</td>"
            f"<td>{len(bundle.neighbor_entity_ids)}</td>"
            f"<td>{len(bundle.relation_edges)}</td>"
            f"<td>{len(bundle.evidence_items)}</td>"
            "</tr>"
        )

    html = f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>Phase-2 标签关系预览</title>
  <style>
    body {{ font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; background: #fffaf2; color: #1f2937; margin: 0; }}
    .wrap {{ max-width: 1080px; margin: 24px auto; padding: 0 16px 28px; }}
    h1 {{ font-size: 24px; margin: 8px 0 16px; color: #9a3412; }}
    h2 {{ font-size: 18px; margin: 22px 0 10px; color: #7c2d12; }}
    .card {{ background: #ffffff; border: 1px solid #fed7aa; border-radius: 12px; padding: 14px; box-shadow: 0 8px 20px rgba(154,52,18,.08); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid #fde68a; padding: 8px 6px; text-align: left; }}
    th {{ background: #fff7ed; }}
    .hint {{ font-size: 12px; color: #6b7280; margin-top: 8px; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>Phase-2 标签关系可视化校验</h1>
    <div class=\"card\">
      <h2>高相关标签对（对称条件概率）</h2>
      <table>
        <thead>
          <tr><th>Label A ID</th><th>Label A</th><th>Label B ID</th><th>Label B</th><th>关联强度</th></tr>
        </thead>
        <tbody>
          {''.join(rows)}
        </tbody>
      </table>
      <div class=\"hint\">关联强度 = P(B|A) + P(A|B)，用于人工抽检关系合理性。</div>
    </div>

    <div class=\"card\" style=\"margin-top:14px;\">
      <h2>标签子图覆盖统计（抽样）</h2>
      <table>
        <thead>
          <tr><th>Label ID</th><th>标签名</th><th>命中实体</th><th>邻域实体</th><th>关系边</th><th>证据条数</th></tr>
        </thead>
        <tbody>
          {''.join(detail_rows)}
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>
"""
    output_file.write_text(html, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="构建 Phase-2 标签外部语义知识层")
    parser.add_argument("--output-dir", type=str, default="outputs/phase2", help="输出目录")
    parser.add_argument("--semantic-top-k", type=int, default=8, help="每个标签语义补全实体数量上限")
    parser.add_argument("--semantic-threshold", type=float, default=0.55, help="语义相似度阈值")
    parser.add_argument("--evidence-top-k", type=int, default=4, help="每个标签补全证据条数")
    parser.add_argument("--preview-limit", type=int, default=12, help="可视化预览标签数")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = ROOT_DIR / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    taxonomy = load_label_taxonomy()
    labels = list_labels(group_id=None, enabled_only=True)
    label_map: Dict[str, LabelDef] = {lb.id: lb for lb in labels}
    label_ids = [lb.id for lb in labels]

    db = SessionLocal()
    try:
        entity_embeddings = _fetch_entity_embeddings(db)
        all_entities = _fetch_all_entities(db)

        bundles: Dict[str, LabelGraphBundle] = {}
        all_entity_type_keys = sorted(list(models.ENTITY_TYPES.keys()))

        enhanced_vectors: Dict[str, Dict[str, Any]] = {}
        for lb in labels:
            bundle = build_label_bundle(
                db=db,
                label=lb,
                all_entities=all_entities,
                entity_embeddings=entity_embeddings,
                semantic_top_k=max(1, int(args.semantic_top_k)),
                semantic_threshold=float(args.semantic_threshold),
                evidence_top_k=max(1, int(args.evidence_top_k)),
            )
            bundles[lb.id] = bundle

            engineering = _build_engineering_features(bundle, all_entity_type_keys)
            semantic_emb = _aggregate_label_semantic_embedding(
                db=db,
                label=lb,
                bundle=bundle,
                entity_embeddings=entity_embeddings,
            )

            enhanced_vectors[lb.id] = {
                "label_id": lb.id,
                "label_name": lb.name,
                "group_id": lb.group_id,
                "seed_terms": bundle.seed_terms,
                "engineering_features": engineering,
                "semantic_embedding": semantic_emb,
                "enhanced_vector": {
                    "dense_features": [engineering[k] for k in sorted(engineering.keys())],
                    "embedding": semantic_emb.get("enhanced_embedding", []),
                },
            }

        matrices = build_relation_matrices(label_ids=label_ids, bundles=bundles, labels_by_id=label_map)

        # 1) 子图与增强向量
        subgraph_payload = {
            "version": "phase2-task2-v1",
            "taxonomy_version": taxonomy.version,
            "labels": {
                lid: {
                    "label_id": b.label_id,
                    "label_name": b.label_name,
                    "seed_terms": b.seed_terms,
                    "entity_ids": sorted(list(b.entity_ids)),
                    "entity_names": b.entity_names,
                    "neighbor_entity_ids": sorted(list(b.neighbor_entity_ids)),
                    "relation_edges": b.relation_edges,
                    "evidence_items": b.evidence_items,
                    "entity_type_counter": b.entity_type_counter,
                }
                for lid, b in bundles.items()
            },
        }

        (out_dir / "label_related_subgraphs.json").write_text(_safe_json_dumps(subgraph_payload), encoding="utf-8")
        (out_dir / "label_enhanced_vectors.json").write_text(_safe_json_dumps(enhanced_vectors), encoding="utf-8")

        # 2) 矩阵与邻接关系
        (out_dir / "label_relation_matrices.json").write_text(_safe_json_dumps(matrices), encoding="utf-8")
        _write_csv_matrix(out_dir / "label_cooccurrence_matrix.csv", label_ids, matrices["cooccurrence_matrix"])
        _write_csv_matrix(out_dir / "label_conditional_probability_matrix.csv", label_ids, matrices["conditional_probability_matrix"])

        # 3) 可视化校验
        _build_preview_html(
            output_file=out_dir / "label_relation_preview.html",
            labels=label_map,
            bundles=bundles,
            matrices=matrices,
            preview_limit=max(6, int(args.preview_limit)),
        )

        print("=" * 72)
        print("Phase-2 任务二构建完成")
        print("=" * 72)
        print(f"输出目录: {out_dir}")
        print(f"标签数量: {len(labels)}")
        print(f"子图文件: {out_dir / 'label_related_subgraphs.json'}")
        print(f"增强向量: {out_dir / 'label_enhanced_vectors.json'}")
        print(f"关系矩阵: {out_dir / 'label_relation_matrices.json'}")
        print(f"共现矩阵CSV: {out_dir / 'label_cooccurrence_matrix.csv'}")
        print(f"条件概率CSV: {out_dir / 'label_conditional_probability_matrix.csv'}")
        print(f"可视化预览: {out_dir / 'label_relation_preview.html'}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
