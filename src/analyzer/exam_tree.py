"""과년도 기출을 과목-카테고리-세부유형 트리로 구성합니다."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from config.config import CONFIG


class ExamTreeBuilder:
    """구조화된 기출 레코드에서 출제 트리 JSON을 생성합니다."""

    def __init__(self, output_path: Path | None = None) -> None:
        """출제 트리 저장 경로를 초기화합니다."""
        self.output_path = output_path or CONFIG.exam_index_dir / "exam_tree.json"

    def build(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """subject -> category -> subcategory 트리를 생성합니다."""
        tree: dict[str, Any] = {}
        for record in records:
            subject = str(record.get("subject") or "미분류")
            category = str(record.get("category") or "미분류")
            subcategory = str(record.get("subcategory") or record.get("sub_category") or "미분류")
            subject_node = tree.setdefault(subject, {"count": 0, "categories": {}})
            category_node = subject_node["categories"].setdefault(category, {"count": 0, "subcategories": {}})
            subcategory_node = category_node["subcategories"].setdefault(
                subcategory,
                {"count": 0, "years": [], "questions": []},
            )
            subject_node["count"] += 1
            category_node["count"] += 1
            subcategory_node["count"] += 1
            year = record.get("year")
            if year and int(year) not in subcategory_node["years"]:
                subcategory_node["years"].append(int(year))
            subcategory_node["questions"].append(
                {
                    "year": record.get("year"),
                    "round": record.get("round"),
                    "question_number": record.get("question_number"),
                }
            )

        for subject_node in tree.values():
            for category_node in subject_node["categories"].values():
                for subcategory_node in category_node["subcategories"].values():
                    subcategory_node["years"] = sorted(subcategory_node["years"])
        return tree

    def save(self, tree: dict[str, Any]) -> Path:
        """출제 트리를 JSON 파일로 저장합니다."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.output_path

    def format_report(self, tree: dict[str, Any], limit: int = 8) -> str:
        """출제 트리를 GUI 출력용 문자열로 변환합니다."""
        if not tree:
            return "출제 트리\n- 데이터 없음"
        lines = ["출제 트리"]
        for subject, subject_node in sorted(tree.items(), key=lambda item: item[1]["count"], reverse=True):
            lines.append(f"- {subject} ({subject_node['count']}문항)")
            categories = sorted(subject_node["categories"].items(), key=lambda item: item[1]["count"], reverse=True)
            for category, category_node in categories[:limit]:
                subcategories = sorted(
                    category_node["subcategories"].items(),
                    key=lambda item: item[1]["count"],
                    reverse=True,
                )
                details = ", ".join(f"{name}({node['count']})" for name, node in subcategories[:limit])
                lines.append(f"  - {category}: {details}")
        return "\n".join(lines)

