"""회차 기준 출제 안정도를 계산합니다."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


class StabilityAnalyzer:
    """전체 회차 대비 출제 회차 비율을 계산합니다."""

    def analyze(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """SubCategory별 안정도 데이터를 반환합니다."""
        exam_keys = sorted({(int(record.get("year") or 0), int(record.get("round") or 0)) for record in records if record.get("year") and record.get("round")})
        total_exams = len(exam_keys)
        appeared: dict[str, set[tuple[int, int]]] = defaultdict(set)
        for record in records:
            subcategory = str(record.get("primary") or record.get("subcategory") or record.get("sub_category") or "")
            if self._is_unclassified(record, subcategory):
                continue
            key = (int(record.get("year") or 0), int(record.get("round") or 0))
            if key[0] and key[1]:
                appeared[subcategory].add(key)
        stability = {}
        for subcategory, keys in appeared.items():
            ratio = round(len(keys) / total_exams * 100, 2) if total_exams else 0
            stability[subcategory] = {
                "exam_count": len(keys),
                "total_exams": total_exams,
                "ratio": ratio,
                "stars": self._stars(ratio),
            }
        return {"total_exams": total_exams, "stability": stability}

    def format_report(self, analysis: dict[str, Any]) -> str:
        """안정도 분석을 문자열로 변환합니다."""
        items = analysis.get("stability", {})
        if not items:
            return "출제 안정도\n- 데이터 없음"
        lines = ["출제 안정도"]
        ordered = sorted(items.items(), key=lambda item: item[1]["ratio"], reverse=True)
        for subcategory, info in ordered[:20]:
            lines.append(
                f"- {subcategory}: {info['exam_count']}회/{info['total_exams']}회 "
                f"({info['ratio']}%) {info['stars']}"
            )
        return "\n".join(lines)

    def score_map(self, analysis: dict[str, Any]) -> dict[str, float]:
        """출제 가능성 계산용 0~1 안정도 점수를 반환합니다."""
        return {
            subcategory: float(info.get("ratio") or 0) / 100
            for subcategory, info in analysis.get("stability", {}).items()
        }

    def _stars(self, ratio: float) -> str:
        if ratio >= 85:
            return "★★★★★"
        if ratio >= 70:
            return "★★★★☆"
        if ratio >= 50:
            return "★★★☆☆"
        if ratio >= 30:
            return "★★☆☆☆"
        return "★☆☆☆☆"

    def _is_unclassified(self, record: dict[str, Any], subcategory: str) -> bool:
        return str(record.get("category") or "") == "미분류" or subcategory == "미분류" or not subcategory

