#!/usr/bin/env python3
"""
导出历史审核样本为训练/标注模板（Phase-1）。

零侵入设计：
- 只读数据库，不修改任何业务数据
- 输出独立文件，可回滚可重跑
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from models.models import AgentFeedback, Story  # noqa: E402
from utils.database import SessionLocal  # noqa: E402


def _safe_parse_payload(text: Optional[str]) -> Dict[str, Any]:
    if not text:
        return {}
    raw = str(text).strip()
    if not raw:
        return {}

    # 优先按 JSON 解析，失败后兼容历史 str(dict) 存储格式。
    try:
        val = json.loads(raw)
        return val if isinstance(val, dict) else {"value": val}
    except Exception:
        pass

    try:
        val = ast.literal_eval(raw)
        return val if isinstance(val, dict) else {"value": val}
    except Exception:
        return {"raw": raw}


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, ensure_ascii=False, default=str)


def _get_attr(instance: Any, name: str, default: Any = None) -> Any:
    """读取 ORM 实例属性，兼容静态类型检查。"""
    value = getattr(instance, name, default)
    return default if value is None else value


def _extract_feedback_text(agent_type: str, payload: Dict[str, Any]) -> str:
    candidates = [
        payload.get("feedback"),
        payload.get("reader_feedback"),
        payload.get("audience_feedback"),
        payload.get("suggestions"),
        payload.get("summary"),
        payload.get("comment"),
    ]

    review_summary = payload.get("review_summary")
    if isinstance(review_summary, dict):
        candidates.append(review_summary.get("overall_assessment"))

    for item in candidates:
        text = _to_text(item)
        if text:
            return text

    # 最后兜底：将 payload 压缩为文本。
    if payload:
        return json.dumps(payload, ensure_ascii=False)
    return f"[{agent_type}] 无可提取反馈文本"


def _extract_revised_content(payload: Dict[str, Any]) -> str:
    for key in ("revised_content", "content", "final_content"):
        text = _to_text(payload.get(key))
        if text:
            return text
    return ""


def _extract_sections(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    sections = payload.get("review_sections")
    if isinstance(sections, list):
        return [s for s in sections if isinstance(s, dict)]

    issues = payload.get("issues")
    if isinstance(issues, list):
        return [{"section_type": "issue", "content": i} for i in issues]

    return []


def _extract_evidence(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    evidence = payload.get("evidence")
    if isinstance(evidence, list):
        return [x for x in evidence if isinstance(x, dict)]

    debug = payload.get("_debug")
    if isinstance(debug, dict):
        return [{"debug": debug}]

    return []


def _build_record(feedback_obj: AgentFeedback, story_obj: Optional[Story]) -> Dict[str, Any]:
    feedback_text_raw = _to_text(_get_attr(feedback_obj, "feedback", ""))
    parsed = _safe_parse_payload(feedback_text_raw)

    story_title = ""
    story_content = ""
    age_group = ""
    style = ""
    target_audience = ""
    extra_requirements = ""

    if story_obj is not None:
        story_title = _to_text(story_obj.theme)
        story_content = _to_text(story_obj.content)
        age_group = _to_text(story_obj.age_group)
        style = _to_text(story_obj.style)
        target_audience = _to_text(story_obj.target_audience)
        extra_requirements = _to_text(story_obj.extra_requirements)

    return {
        "sample_id": f"AF-{_to_text(_get_attr(feedback_obj, 'id', ''))}",
        "source": {
            "feedback_id": _get_attr(feedback_obj, "id", None),
            "story_id": _get_attr(feedback_obj, "story_id", None),
            "agent_type": _to_text(_get_attr(feedback_obj, "agent_type", "")),
            "created_at": _to_text(_get_attr(feedback_obj, "created_at", "")),
        },
        "story": {
            "title": story_title,
            "content": story_content,
            "age_group": age_group,
            "style": style,
            "target_audience": target_audience,
            "extra_requirements": extra_requirements,
        },
        "model_output": {
            "feedback_text": _extract_feedback_text(_to_text(_get_attr(feedback_obj, "agent_type", "")), parsed),
            "revised_content": _extract_revised_content(parsed),
            "review_sections": _extract_sections(parsed),
            "evidence": _extract_evidence(parsed),
            "raw_feedback": feedback_text_raw,
            "parsed_feedback": parsed,
        },
        "annotation": {
            "status": "pending",
            "primary_label_id": "",
            "secondary_label_ids": [],
            "quality_score": None,
            "rationale": "",
            "evidence_spans": [],
            "reviewer": "",
            "reviewed_at": "",
            "notes": "",
        },
    }


def _iter_records(agent_types: List[str], limit: int) -> Iterable[Dict[str, Any]]:
    db = SessionLocal()
    try:
        q = (
            db.query(AgentFeedback, Story)
            .outerjoin(Story, AgentFeedback.story_id == Story.id)
            .order_by(AgentFeedback.created_at.desc())
        )

        if agent_types:
            q = q.filter(AgentFeedback.agent_type.in_(agent_types))

        if limit > 0:
            q = q.limit(limit)

        for feedback_obj, story_obj in q.all():
            yield _build_record(feedback_obj, story_obj)
    finally:
        db.close()


def _filter_records_by_theme_keywords(records: List[Dict[str, Any]], theme_keywords: List[str]) -> List[Dict[str, Any]]:
    if not theme_keywords:
        return records

    normalized = [k.strip().lower() for k in theme_keywords if k.strip()]
    if not normalized:
        return records

    filtered: List[Dict[str, Any]] = []
    for r in records:
        raw_story = r.get("story")
        story: Dict[str, Any] = raw_story if isinstance(raw_story, dict) else {}
        title = str(story.get("title") or "").strip().lower()
        if any(k in title for k in normalized):
            filtered.append(r)
    return filtered


def _sample_records_per_theme(records: List[Dict[str, Any]], sample_per_theme: int, random_seed: int) -> List[Dict[str, Any]]:
    if sample_per_theme <= 0:
        return records

    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        raw_story = r.get("story")
        story: Dict[str, Any] = raw_story if isinstance(raw_story, dict) else {}
        theme = str(story.get("title") or "").strip() or "__UNKNOWN_THEME__"
        buckets.setdefault(theme, []).append(r)

    rng = random.Random(random_seed)
    sampled: List[Dict[str, Any]] = []
    for theme in sorted(buckets.keys()):
        items = list(buckets[theme])
        rng.shuffle(items)
        sampled.extend(items[:sample_per_theme])
    return sampled


def _write_jsonl(records: Iterable[Dict[str, Any]], output_file: Path) -> int:
    count = 0
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            count += 1
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导出历史样本模板（JSONL）")
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/phase1/historical_samples_template.jsonl",
        help="输出 JSONL 文件路径",
    )
    parser.add_argument(
        "--agent-types",
        type=str,
        default="science_checker,science_checker_self_feedback,literature_checker,reader,reader_refine",
        help="逗号分隔的 agent_type 白名单",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="最多导出条数，<=0 表示不限制",
    )
    parser.add_argument(
        "--theme-keywords",
        type=str,
        default="",
        help="按故事主题关键词过滤，逗号分隔，如：地球,光合作用",
    )
    parser.add_argument(
        "--sample-per-theme",
        type=int,
        default=0,
        help="每个主题最多抽样条数，<=0 表示不启用主题抽样",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="主题抽样随机种子（保证可复现）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_file = ROOT_DIR / args.output

    agent_types = [x.strip() for x in str(args.agent_types).split(",") if x.strip()]
    theme_keywords = [x.strip() for x in str(args.theme_keywords).split(",") if x.strip()]

    base_limit = args.limit
    if theme_keywords or args.sample_per_theme > 0:
        # 启用主题过滤/抽样时先拉取候选集合，再执行后处理。
        base_limit = 0

    records = list(_iter_records(agent_types=agent_types, limit=base_limit))
    records = _filter_records_by_theme_keywords(records, theme_keywords)
    records = _sample_records_per_theme(records, sample_per_theme=args.sample_per_theme, random_seed=args.random_seed)

    if args.limit > 0:
        records = records[: args.limit]

    count = _write_jsonl(records, output_file)

    unique_themes = set()
    for r in records:
        raw_story = r.get("story")
        story: Dict[str, Any] = raw_story if isinstance(raw_story, dict) else {}
        unique_themes.add(str(story.get("title") or "").strip() or "__UNKNOWN_THEME__")

    print("=" * 64)
    print("历史样本模板导出完成")
    print("=" * 64)
    print(f"输出文件: {output_file}")
    print(f"样本条数: {count}")
    print(f"过滤 agent_types: {agent_types}")
    print(f"主题关键词: {theme_keywords if theme_keywords else '未启用'}")
    print(f"每主题抽样: {args.sample_per_theme if args.sample_per_theme > 0 else '未启用'}")
    print(f"覆盖主题数: {len(unique_themes)}")


if __name__ == "__main__":
    main()
