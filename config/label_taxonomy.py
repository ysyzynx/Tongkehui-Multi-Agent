from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class LabelDef:
    id: str
    name: str
    group_id: str
    aliases: List[str]
    definition: str
    positive_hints: List[str]
    negative_hints: List[str]
    priority: int
    enabled: bool


@dataclass(frozen=True)
class LabelGroup:
    group_id: str
    group_name: str
    description: str
    labels: List[LabelDef]


@dataclass(frozen=True)
class LabelTaxonomy:
    version: str
    updated_at: str
    groups: List[LabelGroup]

    @property
    def labels(self) -> List[LabelDef]:
        merged: List[LabelDef] = []
        for g in self.groups:
            merged.extend(g.labels)
        return merged

    @property
    def label_id_map(self) -> Dict[str, LabelDef]:
        return {label.id: label for label in self.labels}

    @property
    def label_name_map(self) -> Dict[str, LabelDef]:
        return {label.name: label for label in self.labels}


def _taxonomy_file() -> Path:
    return Path(__file__).with_name("label_taxonomy_v1.json")


def load_label_taxonomy() -> LabelTaxonomy:
    data = json.loads(_taxonomy_file().read_text(encoding="utf-8"))

    groups: List[LabelGroup] = []
    for g in data.get("groups", []):
        labels: List[LabelDef] = []
        for item in g.get("labels", []):
            labels.append(
                LabelDef(
                    id=str(item["id"]),
                    name=str(item["name"]),
                    group_id=str(g["group_id"]),
                    aliases=[str(x) for x in item.get("aliases", [])],
                    definition=str(item.get("definition", "")),
                    positive_hints=[str(x) for x in item.get("positive_hints", [])],
                    negative_hints=[str(x) for x in item.get("negative_hints", [])],
                    priority=int(item.get("priority", 9999)),
                    enabled=bool(item.get("enabled", True)),
                )
            )

        groups.append(
            LabelGroup(
                group_id=str(g["group_id"]),
                group_name=str(g.get("group_name", g["group_id"])),
                description=str(g.get("description", "")),
                labels=labels,
            )
        )

    return LabelTaxonomy(
        version=str(data.get("version", "unknown")),
        updated_at=str(data.get("updated_at", "")),
        groups=groups,
    )


def validate_label_taxonomy(taxonomy: Optional[LabelTaxonomy] = None) -> List[str]:
    t = taxonomy or load_label_taxonomy()
    errors: List[str] = []

    seen_ids = set()
    seen_names = set()
    for label in t.labels:
        if label.id in seen_ids:
            errors.append(f"duplicate label id: {label.id}")
        seen_ids.add(label.id)

        if label.name in seen_names:
            errors.append(f"duplicate label name: {label.name}")
        seen_names.add(label.name)

        if not label.definition.strip():
            errors.append(f"missing definition: {label.id}")

        if not label.positive_hints:
            errors.append(f"missing positive_hints: {label.id}")

    return errors


def get_label_by_id(label_id: str) -> Optional[LabelDef]:
    taxonomy = load_label_taxonomy()
    return taxonomy.label_id_map.get(label_id)


def get_label_by_name(label_name: str) -> Optional[LabelDef]:
    taxonomy = load_label_taxonomy()
    return taxonomy.label_name_map.get(label_name)


def list_labels(group_id: Optional[str] = None, enabled_only: bool = True) -> List[LabelDef]:
    taxonomy = load_label_taxonomy()
    labels = taxonomy.labels
    if group_id:
        labels = [x for x in labels if x.group_id == group_id]
    if enabled_only:
        labels = [x for x in labels if x.enabled]
    return sorted(labels, key=lambda x: x.priority)
