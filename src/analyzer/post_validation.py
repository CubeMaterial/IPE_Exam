"""기출 분류 결과를 exam_taxonomy 기준으로 사후 검증합니다."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from config.config import BASE_DIR, CONFIG


UNCLASSIFIED = {
    "subject": "미분류",
    "category": "미분류",
    "subcategory": "미분류",
    "sub_category": "미분류",
    "primary": "미분류",
    "secondary": [],
}


class ClassificationValidator:
    """subject/category/subcategory 계층 조합을 검증합니다."""

    def __init__(
        self,
        taxonomy_path: Path | None = None,
        invalid_path: Path | None = None,
    ) -> None:
        """검증 기준 파일과 실패 기록 경로를 초기화합니다."""
        self.taxonomy_path = taxonomy_path or BASE_DIR / "config" / "exam_taxonomy.json"
        self.invalid_path = invalid_path or CONFIG.exam_index_dir / "invalid_classifications.json"
        self.taxonomy = self._load_taxonomy()

    def validate_classification(self, item: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        """분류 결과를 검증하고 잘못된 조합은 미분류로 초기화합니다."""
        normalized = deepcopy(item)
        normalized.setdefault("secondary", [])
        subject = str(normalized.get("subject") or "")
        category = str(normalized.get("category") or "")
        subcategory = str(normalized.get("subcategory") or normalized.get("sub_category") or "")
        primary = str(normalized.get("primary") or subcategory or "")

        if category == "미분류" or subcategory == "미분류" or subject == "미분류":
            if any(value and value != "미분류" for value in (subject, category, subcategory, primary)):
                self.record_invalid(normalized, "미분류 조합에 값이 섞임", context)
            return self._unclassified(normalized)

        reason = self._invalid_reason(subject, category, subcategory)
        if reason:
            self.record_invalid(normalized, reason, context)
            return self._unclassified(normalized)

        allowed = self.allowed_subcategories(subject, category)
        if primary not in allowed:
            primary = subcategory
        secondary = [
            str(value).strip()
            for value in self._as_list(normalized.get("secondary"))
            if str(value).strip() in allowed and str(value).strip() != primary
        ]
        normalized["subcategory"] = subcategory
        normalized["sub_category"] = subcategory
        normalized["primary"] = primary
        normalized["secondary"] = list(dict.fromkeys(secondary))
        return normalized

    def record_invalid(self, item: dict[str, Any], reason: str, context: dict[str, Any] | None = None) -> None:
        """잘못된 분류 조합을 invalid_classifications.json에 누적 저장합니다."""
        self.invalid_path.parent.mkdir(parents=True, exist_ok=True)
        existing = []
        if self.invalid_path.exists():
            try:
                data = json.loads(self.invalid_path.read_text(encoding="utf-8"))
                existing = data if isinstance(data, list) else []
            except json.JSONDecodeError:
                existing = []
        entry = {
            "reason": reason,
            "subject": item.get("subject", ""),
            "category": item.get("category", ""),
            "subcategory": item.get("subcategory", item.get("sub_category", "")),
            "primary": item.get("primary", ""),
            "secondary": item.get("secondary", []),
            "context": context or {},
        }
        if entry not in existing:
            existing.append(entry)
        self.invalid_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    def invalid_records(self) -> list[dict[str, Any]]:
        """저장된 검증 실패 기록을 반환합니다."""
        if not self.invalid_path.exists():
            return []
        try:
            data = json.loads(self.invalid_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []

    def format_invalid_report(self) -> str:
        """검증 실패 분류 섹션을 문자열로 생성합니다."""
        records = self.invalid_records()
        lines = ["검증 실패 분류"]
        if not records:
            lines.append("- 없음")
            return "\n".join(lines)
        for record in records[-30:]:
            lines.append(
                f"- {record.get('subject')} / {record.get('category')} / {record.get('subcategory')} "
                f"→ {record.get('reason')}"
            )
        return "\n".join(lines)

    def allowed_subcategories(self, subject: str, category: str) -> set[str]:
        """subject/category 아래 허용된 subcategory 집합을 반환합니다."""
        values = self.taxonomy.get(subject, {}).get(category, [])
        return set(values)

    def subject_for_category(self, category: str) -> str:
        """카테고리가 속한 첫 subject를 반환합니다."""
        for subject, categories in self.taxonomy.items():
            if category in categories:
                return subject
        return "미분류"

    def _invalid_reason(self, subject: str, category: str, subcategory: str) -> str:
        if subject not in self.taxonomy:
            return "taxonomy subject 불일치"
        if category not in self.taxonomy[subject]:
            return "taxonomy category 불일치"
        if subcategory not in self.taxonomy[subject][category]:
            return "taxonomy subcategory 불일치"
        return ""

    def _unclassified(self, item: dict[str, Any]) -> dict[str, Any]:
        result = deepcopy(item)
        result.update(UNCLASSIFIED)
        return result

    def _load_taxonomy(self) -> dict[str, dict[str, list[str]]]:
        try:
            data = json.loads(self.taxonomy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _as_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        return [item.strip() for item in str(value or "").split(",") if item.strip()]


def validate_classification(item: dict[str, Any]) -> dict[str, Any]:
    """편의 함수: 기본 taxonomy로 분류 결과를 검증합니다."""
    return ClassificationValidator().validate_classification(item)
