#!/usr/bin/env python3
"""
基于历史样本模板生成标注任务模板（Phase-1）。

输入: historical_samples_template.jsonl
输出:
- annotation_tasks.jsonl (按样本生成任务)
- annotation_matrix.csv  (按样本 x 候选标签展开)
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from config.label_taxonomy import list_labels  # noqa: E402


def _read_jsonl(input_file: Path) -> Iterable[Dict[str, Any]]:
    with input_file.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                obj = json.loads(text)
                if isinstance(obj, dict):
                    yield obj
            except Exception:
                print(f"[WARN] 第{idx}行不是合法JSON，已跳过")


def _group_id_for_agent(agent_type: str) -> str:
    lower = (agent_type or "").lower()
    if "science" in lower:
        return "SCIENCE_REVIEW"
    return "VALUE_TAG"


def _build_text_for_annotation(sample: Dict[str, Any], max_chars: int) -> str:
    raw_model_output = sample.get("model_output")
    raw_story = sample.get("story")
    model_output: Dict[str, Any] = raw_model_output if isinstance(raw_model_output, dict) else {}
    story: Dict[str, Any] = raw_story if isinstance(raw_story, dict) else {}

    title = str(story.get("title") or "").strip()
    content = str(story.get("content") or "").strip()
    feedback_text = str(model_output.get("feedback_text") or "").strip()
    revised_content = str(model_output.get("revised_content") or "").strip()

    parts = []
    if title:
        parts.append(f"[标题]\n{title}")
    if content:
        parts.append(f"[原文]\n{content}")
    if feedback_text:
        parts.append(f"[反馈]\n{feedback_text}")
    if revised_content:
        parts.append(f"[修订]\n{revised_content}")

    merged = "\n\n".join(parts)
    if len(merged) > max_chars:
        merged = merged[: max_chars - 30] + "\n\n[TRUNCATED]"
    return merged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成标注任务模板")
    parser.add_argument(
        "--input",
        type=str,
        default="outputs/phase1/historical_samples_template.jsonl",
        help="输入历史样本 JSONL",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/phase1",
        help="输出目录",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=6000,
        help="单条样本文本截断上限",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_file = ROOT_DIR / args.input
    output_dir = ROOT_DIR / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    tasks_file = output_dir / "annotation_tasks.jsonl"
    matrix_file = output_dir / "annotation_matrix.csv"

    samples = list(_read_jsonl(input_file))
    if not samples:
        print(f"[WARN] 输入为空: {input_file}")
        return

    task_count = 0
    matrix_rows = 0

    with tasks_file.open("w", encoding="utf-8") as tf, matrix_file.open("w", encoding="utf-8", newline="") as cf:
        writer = csv.writer(cf)
        writer.writerow(
            [
                "task_id",
                "sample_id",
                "agent_type",
                "label_id",
                "label_name",
                "label_definition",
                "decision",
                "confidence",
                "rationale",
                "evidence_quote",
                "reviewer",
                "reviewed_at",
            ]
        )

        for sample in samples:
            raw_source = sample.get("source")
            source: Dict[str, Any] = raw_source if isinstance(raw_source, dict) else {}
            sample_id = str(sample.get("sample_id") or "")
            agent_type = str(source.get("agent_type") or "")

            group_id = _group_id_for_agent(agent_type)
            candidates = list_labels(group_id=group_id, enabled_only=True)

            task = {
                "task_id": f"TASK-{sample_id}",
                "sample_id": sample_id,
                "agent_type": agent_type,
                "group_id": group_id,
                "text_for_annotation": _build_text_for_annotation(sample, max_chars=args.max_chars),
                "candidate_labels": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "definition": c.definition,
                        "aliases": c.aliases,
                        "positive_hints": c.positive_hints,
                        "negative_hints": c.negative_hints,
                    }
                    for c in candidates
                ],
                "answer_template": {
                    "primary_label_id": "",
                    "secondary_label_ids": [],
                    "quality_score": "",
                    "rationale": "",
                    "evidence_spans": [],
                    "reviewer": "",
                    "reviewed_at": "",
                },
            }
            tf.write(json.dumps(task, ensure_ascii=False) + "\n")
            task_count += 1

            for c in candidates:
                writer.writerow(
                    [
                        task["task_id"],
                        sample_id,
                        agent_type,
                        c.id,
                        c.name,
                        c.definition,
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                    ]
                )
                matrix_rows += 1

    print("=" * 64)
    print("标注模板生成完成")
    print("=" * 64)
    print(f"输入样本: {input_file}")
    print(f"任务文件: {tasks_file}")
    print(f"矩阵文件: {matrix_file}")
    print(f"任务数: {task_count}")
    print(f"矩阵行数: {matrix_rows}")


if __name__ == "__main__":
    main()
