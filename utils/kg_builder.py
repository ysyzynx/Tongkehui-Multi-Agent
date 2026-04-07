"""
知识图谱构建工具
支持从文档、维基百科提取实体和关系
"""
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_

from models import models
from utils.llm_client import llm_client
from prompts.kg_prompts import get_entity_extraction_prompt
from utils.wikipedia_client import get_wikipedia_page_content, search_wikipedia


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


def normalize_entity_name(name: str) -> str:
    """标准化实体名称"""
    if not name:
        return ""
    # 移除首尾空格
    name = name.strip()
    # 统一中文标点
    return name


def _clean_candidate_name(raw: str) -> str:
    """清洗规则抽取得到的候选实体名称。"""
    if not raw:
        return ""
    cleaned = raw.strip().strip("，。；：:,.!?！？()（）[]【】\"'“”")
    if len(cleaned) < 2 or len(cleaned) > 30:
        return ""
    return cleaned


def _normalize_relation_label(raw: Any) -> str:
    """清洗 LLM 给出的关系短语。"""
    text = str(raw or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", "", text)
    text = text.strip("，。；：:,.!?！？()（）[]【】\"'“”")
    # 强制控制关系长度限制，避免出现长句。LLM生成合理的动宾短语通常在2~6个字。
    if len(text) < 1 or len(text) > 8:
        return ""
    return text


def _extract_relation_label_from_llm(r_data: Dict[str, Any]) -> str:
    """优先提取 LLM 的关系谓词，如“围绕公转”“遮挡形成”。严禁使用长句描述。"""
    for candidate in [
        r_data.get("relation_text"),
        r_data.get("predicate"),
        r_data.get("relation"),
        # 不再使用 description 作为 relation_label fallback，因为它通常是一句长话
    ]:
        label = _normalize_relation_label(candidate)
        if label:
            return label
    return ""


def _rule_based_extract(text: str, source_document_id: Optional[int] = None) -> Tuple[List[Dict], List[Dict]]:
    """LLM 不可用时的兜底规则抽取，保证基础可用性。"""
    entities_map: Dict[str, Dict[str, Any]] = {}
    relations: List[Dict[str, Any]] = []

    def add_entity(name: str):
        if name not in entities_map:
            entities_map[name] = {
                "name": name,
                "entity_type": "CONCEPT",
                "description": "",
                "confidence": 0.55,
                "source_document_id": source_document_id,
            }

    sentence_patterns = [
        (re.compile(r"(?P<source>[^，。,；;：:\n]{1,20})是(?P<target>[^，。,；;：:\n]{1,20})"), "IS_A"),
        (re.compile(r"(?P<source>[^，。,；;：:\n]{1,20})属于(?P<target>[^，。,；;：:\n]{1,20})"), "IS_A"),
        (re.compile(r"(?P<source>[^，。,；;：:\n]{1,20})包含(?P<target>[^，。,；;：:\n]{1,20})"), "HAS_PART"),
        (re.compile(r"(?P<source>[^，。,；;：:\n]{1,20})导致(?P<target>[^，。,；;：:\n]{1,20})"), "CAUSES"),
    ]

    sentences = [s.strip() for s in re.split(r"[。！？!?\n]+", text) if s and s.strip()]
    for sentence in sentences:
        for pattern, relation_type in sentence_patterns:
            match = pattern.search(sentence)
            if not match:
                continue

            source_name = _clean_candidate_name(match.group("source"))
            target_name = _clean_candidate_name(match.group("target"))
            if not source_name or not target_name or source_name == target_name:
                continue

            add_entity(source_name)
            add_entity(target_name)
            relations.append({
                "source_name": source_name,
                "target_name": target_name,
                "relation_type": relation_type,
                "description": sentence[:80],
                "confidence": 0.55,
                "source_document_id": source_document_id,
            })

    # 没识别到关系时，至少抽取部分候选概念，避免前端“无任何结果”。
    if not entities_map:
        tokens = re.split(r"[，,、；;：:\s]+", text[:160])
        for token in tokens:
            candidate = _clean_candidate_name(token)
            if candidate:
                add_entity(candidate)
            if len(entities_map) >= 6:
                break

    return list(entities_map.values()), relations


def _dedupe_and_refine_relations(
    relations: List[Dict[str, Any]],
    name_to_entity: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """关系后处理：去自环、去重、同对实体仅保留更有信息量的关系。"""
    if not relations:
        return []

    relation_priority = {
        "IS_A": 9,
        "PART_OF": 8,
        "HAS_PART": 8,
        "CAUSES": 7,
        "IS_CAUSED_BY": 7,
        "DISCOVERED_BY": 6,
        "EXAMPLE_OF": 6,
        "LIVES_IN": 5,
        "SIMILAR_TO": 4,
        "CONTRASTS_WITH": 4,
        "INTERACTS_WITH": 3,
        "RELATED_TO": 2,
    }

    # 1) 精确三元组去重：同 (source, target, type, relation_label) 只留最优一条。
    triple_map: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    for relation in relations:
        source_name = normalize_entity_name(relation.get("source_name", ""))
        target_name = normalize_entity_name(relation.get("target_name", ""))
        relation_type = relation.get("relation_type", "RELATED_TO")
        relation_label = _normalize_relation_label(relation.get("relation_label", ""))

        if not source_name or not target_name:
            continue
        if source_name == target_name:
            # 删除自环关系，例如 <太阳系, HAS_PART, 太阳系>
            continue
        if source_name not in name_to_entity or target_name not in name_to_entity:
            continue

        key = (source_name, target_name, relation_type, relation_label)
        current = triple_map.get(key)
        if current is None:
            triple_map[key] = {
                **relation,
                "source_name": source_name,
                "target_name": target_name,
                "relation_type": relation_type,
                "relation_label": relation_label,
            }
            continue

        old_score = float(current.get("confidence", 0.0))
        new_score = float(relation.get("confidence", 0.0))
        if new_score > old_score:
            triple_map[key] = {
                **relation,
                "source_name": source_name,
                "target_name": target_name,
                "relation_type": relation_type,
                "relation_label": relation_label,
            }

    deduped = list(triple_map.values())

    # 2) 同方向实体对去弱关系：若同 (source,target) 出现多种关系，优先保留高优先级关系。
    pair_best: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for relation in deduped:
        pair_key = (relation["source_name"], relation["target_name"])
        best = pair_best.get(pair_key)
        if best is None:
            pair_best[pair_key] = relation
            continue

        best_priority = relation_priority.get(best.get("relation_type", "RELATED_TO"), 0)
        cur_priority = relation_priority.get(relation.get("relation_type", "RELATED_TO"), 0)
        if cur_priority > best_priority:
            pair_best[pair_key] = relation
            continue
        if cur_priority == best_priority:
            best_score = float(best.get("confidence", 0.0))
            cur_score = float(relation.get("confidence", 0.0))
            best_has_label = bool(_normalize_relation_label(best.get("relation_label", "")))
            cur_has_label = bool(_normalize_relation_label(relation.get("relation_label", "")))
            if cur_has_label and not best_has_label:
                pair_best[pair_key] = relation
                continue
            if cur_score > best_score:
                pair_best[pair_key] = relation

    refined = list(pair_best.values())

    # 3) 控制关系密度，避免边过多导致图谱混乱。
    max_relations = max(6, len(name_to_entity) * 2)
    refined.sort(
        key=lambda item: (
            relation_priority.get(item.get("relation_type", "RELATED_TO"), 0),
            float(item.get("confidence", 0.0)),
        ),
        reverse=True,
    )
    return refined[:max_relations]


def find_entity_by_name(db: Session, name: str) -> Optional[models.KnowledgeGraphEntity]:
        """通过名称查找实体（模糊匹配）"""
        normalized = normalize_entity_name(name)
        if not normalized:
            return None

        # 先精确匹配
        entity = db.query(models.KnowledgeGraphEntity).filter(
            models.KnowledgeGraphEntity.name == normalized
        ).first()
        if entity:
            return entity

        # 模糊匹配
        entity = db.query(models.KnowledgeGraphEntity).filter(
            models.KnowledgeGraphEntity.name.contains(normalized)
        ).first()
        if entity:
            return entity

        # 别名匹配
        entities = db.query(models.KnowledgeGraphEntity).all()
        for e in entities:
            aliases = _safe_json_loads(e.aliases, [])
            if normalized in aliases or any(normalized in a for a in aliases):
                return e

        return None


class KnowledgeGraphBuilder:
    """知识图谱构建器"""

    def __init__(self, db: Session):
        self.db = db

    async def extract_from_text(
        self,
        text: str,
        source_document_id: Optional[int] = None,
        auto_save: bool = True
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        从文本中提取实体和关系
        返回 (实体列表, 关系列表)
        """
        if not text or len(text.strip()) < 10:
            return [], []

        # 使用LLM提取
        prompt = get_entity_extraction_prompt(text[:8000])  # 限制长度

        try:
            result = llm_client.generate_json(
                "你是一个严格遵守格式的知识图谱抽取助手。",
                prompt,
            )
            if not isinstance(result, dict):
                return [], []

            entities_data = result.get("entities", [])
            relations_data = result.get("relations", [])

            # 验证和清理
            entities = []
            name_to_entity = {}

            for e_data in entities_data:
                name = normalize_entity_name(e_data.get("name", ""))
                if not name:
                    continue

                entity_type = e_data.get("type", "CONCEPT")
                # 验证实体类型
                if entity_type not in models.ENTITY_TYPES:
                    entity_type = "CONCEPT"

                entity_dict = {
                    "name": name,
                    "entity_type": entity_type,
                    "description": e_data.get("description", ""),
                    "confidence": float(e_data.get("confidence", 0.8)),
                    "source_document_id": source_document_id,
                }
                entities.append(entity_dict)
                name_to_entity[name] = entity_dict

            # 处理关系
            relations = []
            for r_data in relations_data:
                source_name = normalize_entity_name(r_data.get("source", ""))
                target_name = normalize_entity_name(r_data.get("target", ""))

                if not source_name or not target_name:
                    continue

                if source_name not in name_to_entity or target_name not in name_to_entity:
                    continue

                relation_type = r_data.get("type", "RELATED_TO")
                if relation_type not in models.RELATION_TYPES:
                    relation_type = "RELATED_TO"

                relations.append({
                    "source_name": source_name,
                    "target_name": target_name,
                    "relation_type": relation_type,
                    "description": r_data.get("description", ""),
                    "relation_label": _extract_relation_label_from_llm(r_data),
                    "confidence": float(r_data.get("confidence", 0.8)),
                    "source_document_id": source_document_id,
                })

            relations = _dedupe_and_refine_relations(relations, name_to_entity)

            if not entities:
                entities, relations = _rule_based_extract(text, source_document_id)
                name_to_entity = {item.get("name", ""): item for item in entities if item.get("name")}
                relations = _dedupe_and_refine_relations(relations, name_to_entity)

            if auto_save:
                saved_entities, saved_relations = self._save_extracted(entities, relations)
                return saved_entities, saved_relations

            return entities, relations

        except Exception as e:
            print(f"[extract_from_text] 错误: {e}")
            import traceback
            traceback.print_exc()
            fallback_entities, fallback_relations = _rule_based_extract(text, source_document_id)
            name_to_entity = {item.get("name", ""): item for item in fallback_entities if item.get("name")}
            fallback_relations = _dedupe_and_refine_relations(fallback_relations, name_to_entity)
            if auto_save and fallback_entities:
                return self._save_extracted(fallback_entities, fallback_relations)
            return fallback_entities, fallback_relations

    async def extract_from_topic(
        self,
        topic: str,
        auto_save: bool = True,
    ) -> Tuple[List[Dict], List[Dict], str]:
        """仅依托 LLM：先按词条生成科普片段，再抽取知识图谱。"""
        cleaned_topic = normalize_entity_name(topic)
        if not cleaned_topic:
            return [], [], ""

        system_prompt = "你是儿童科普写作助手，请输出准确、简洁、结构化的科学说明。"
        user_prompt = (
            f"请围绕“{cleaned_topic}”写一段 120-220 字的科普说明，"
            "至少包含2个科学概念和1个明确因果/包含/分类关系。"
            "不要分点，不要Markdown，只输出正文。"
        )

        generated_text = llm_client.generate_text(system_prompt, user_prompt).strip()
        if not generated_text or generated_text.startswith("<!-- 生成失败"):
            generated_text = f"{cleaned_topic} 是一个重要科学概念，它与能量转换、物质变化和自然规律相关。"

        entities, relations = await self.extract_from_text(
            text=generated_text,
            source_document_id=None,
            auto_save=auto_save,
        )
        return entities, relations, generated_text

    def _save_extracted(
        self,
        entities_data: List[Dict],
        relations_data: List[Dict]
    ) -> Tuple[List[Dict], List[Dict]]:
        """保存提取的实体和关系到数据库"""
        saved_entities = []
        name_to_id = {}

        # 保存实体
        for e_data in entities_data:
            # 检查是否已存在
            existing = find_entity_by_name(self.db, e_data["name"])
            if existing:
                # 更新置信度（取最大值）
                if e_data.get("confidence", 0) > existing.confidence:
                    existing.confidence = e_data.get("confidence")
                    if e_data.get("description"):
                        existing.description = e_data.get("description")
                saved_entities.append(self._entity_to_dict(existing))
                name_to_id[e_data["name"]] = existing.id
                continue

            # 创建新实体
            entity = models.KnowledgeGraphEntity(
                name=e_data["name"],
                entity_type=e_data["entity_type"],
                description=e_data.get("description"),
                aliases=None,
                properties=None,
                source_document_id=e_data.get("source_document_id"),
                confidence=e_data.get("confidence", 0.8),
            )
            self.db.add(entity)
            self.db.flush()

            # 生成向量嵌入
            try:
                embedding_text = f"{entity.name} {entity.description or ''}"
                embedding = llm_client.generate_embedding(embedding_text)
                embedding_row = models.KnowledgeGraphEntityEmbedding(
                    entity_id=entity.id,
                    embedding=_safe_json_dumps(embedding),
                )
                self.db.add(embedding_row)
            except Exception as e:
                print(f"[save_extracted] 嵌入生成失败: {e}")

            saved_entities.append(self._entity_to_dict(entity))
            name_to_id[e_data["name"]] = entity.id

        self.db.commit()

        # 保存关系
        saved_relations = []
        relation_seen = set()
        for r_data in relations_data:
            source_id = name_to_id.get(r_data["source_name"])
            target_id = name_to_id.get(r_data["target_name"])

            if not source_id or not target_id:
                continue

            relation_key = (source_id, target_id, r_data["relation_type"])
            if relation_key in relation_seen:
                continue
            relation_seen.add(relation_key)

            relation_label = _normalize_relation_label(r_data.get("relation_label", ""))
            relation_props = {"relation_label": relation_label} if relation_label else None

            # 检查关系是否已存在
            existing = self.db.query(models.KnowledgeGraphRelation).filter(
                models.KnowledgeGraphRelation.source_entity_id == source_id,
                models.KnowledgeGraphRelation.target_entity_id == target_id,
                models.KnowledgeGraphRelation.relation_type == r_data["relation_type"],
            ).first()

            if existing:
                if r_data.get("confidence", 0) > existing.confidence:
                    existing.confidence = r_data.get("confidence")
                    if r_data.get("description"):
                        existing.description = r_data.get("description")
                if relation_props:
                    existing.properties = _safe_json_dumps(relation_props)
                saved_relations.append(self._relation_to_dict(existing))
                continue

            # 创建新关系
            relation = models.KnowledgeGraphRelation(
                source_entity_id=source_id,
                target_entity_id=target_id,
                relation_type=r_data["relation_type"],
                description=r_data.get("description"),
                properties=_safe_json_dumps(relation_props) if relation_props else None,
                source_document_id=r_data.get("source_document_id"),
                confidence=r_data.get("confidence", 0.8),
            )
            self.db.add(relation)
            saved_relations.append(self._relation_to_dict(relation))

        self.db.commit()

        return saved_entities, saved_relations

    async def extract_from_document(
        self,
        document_id: int,
        auto_save: bool = True
    ) -> Tuple[List[Dict], List[Dict]]:
        """从知识库文档中提取实体和关系"""
        doc = self.db.query(models.KnowledgeDocument).filter(
            models.KnowledgeDocument.id == document_id
        ).first()

        if not doc:
            return [], []

        return await self.extract_from_text(
            doc.content,
            source_document_id=document_id,
            auto_save=auto_save
        )

    async def extract_from_wikipedia(
        self,
        title: str,
        language: str = "zh",
        auto_save: bool = True,
        doc_type: str = "SCIENCE_FACT"
    ) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        从维基百科页面提取知识图谱
        返回 (实体列表, 关系列表, 文档信息)
        """
        try:
            # 先按标题直取，失败后回退到搜索首条结果
            page = get_wikipedia_page_content(title=title, language=language)
            if not page:
                search_results = search_wikipedia(title, limit=1, language=language)
                if search_results:
                    page = get_wikipedia_page_content(
                        pageid=search_results[0].get("pageid"),
                        language=language,
                    )

            if not page or not page.get("content"):
                return [], [], {}

            # 提取实体和关系
            entities, relations = await self.extract_from_text(
                page.get("content", ""),
                source_document_id=None,
                auto_save=False,  # 稍后手动保存，先提取
            )

            # 创建知识库文档（可选）
            doc_info = {
                "source_name": f"维基百科: {page.get('title', title)}",
                "source_url": page.get("url"),
                "publisher": "维基百科",
                "author": None,
                "publish_year": None,
                "authority_level": 90,
                "doc_type": doc_type,
                "topic_tags": page.get("categories", [])[:8] or ["百科知识"],
                "content": page.get("content", ""),
            }

            if auto_save:
                # 保存到知识图谱
                saved_entities, saved_relations = self._save_extracted(
                    entities, relations
                )
                return saved_entities, saved_relations, doc_info

            return entities, relations, doc_info

        except Exception as e:
            print(f"[extract_from_wikipedia] 错误: {e}")
            import traceback
            traceback.print_exc()
            return [], [], {}

    async def build_from_knowledge_base(
        self,
        limit: Optional[int] = None,
        start_from: int = 0
    ) -> Dict[str, Any]:
        """
        从整个知识库构建图谱
        """
        query = self.db.query(models.KnowledgeDocument)
        if limit:
            query = query.offset(start_from).limit(limit)

        docs = query.all()

        total_entities = 0
        total_relations = 0
        success_count = 0
        failed_count = 0

        for doc in docs:
            try:
                entities, relations = await self.extract_from_document(
                    doc.id, auto_save=True
                )
                total_entities += len(entities)
                total_relations += len(relations)
                success_count += 1
            except Exception as e:
                print(f"处理文档 {doc.id} 失败: {e}")
                failed_count += 1

        return {
            "processed_docs": len(docs),
            "success_count": success_count,
            "failed_count": failed_count,
            "total_entities": total_entities,
            "total_relations": total_relations,
        }

    def _entity_to_dict(self, entity: models.KnowledgeGraphEntity) -> Dict:
        return {
            "id": entity.id,
            "name": entity.name,
            "entity_type": entity.entity_type,
            "description": entity.description,
            "confidence": entity.confidence,
            "source_document_id": entity.source_document_id,
        }

    def _relation_to_dict(self, relation: models.KnowledgeGraphRelation) -> Dict:
        return {
            "id": relation.id,
            "source_entity_id": relation.source_entity_id,
            "target_entity_id": relation.target_entity_id,
            "relation_type": relation.relation_type,
            "description": relation.description,
            "confidence": relation.confidence,
            "source_document_id": relation.source_document_id,
        }
