"""세부유형별 최근 미출제 공백을 계산합니다."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from config.config import CONFIG


class GapAnalyzer:
    """연도-회차 순서 기준으로 SubCategory의 출제 공백을 계산합니다."""

    def __init__(self, output_path: Path | None = None) -> None:
        """공백 분석 저장 경로를 초기화합니다."""
        self.output_path = output_path or CONFIG.exam_index_dir / "exam_gap.json"

    def analyze(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """각 세부유형의 최근 미출제 회차 수를 계산합니다."""
        exam_keys = self._exam_keys(records)
        positions = {key: index for index, key in enumerate(exam_keys)}
        appeared: dict[str, set[int]] = defaultdict(set)
        for record in records:
            key = (int(record.get("year") or 0), int(record.get("round") or 0))
            subcategory = str(record.get("subcategory") or record.get("sub_category") or "")
            if key in positions and subcategory and not self._is_unclassified(record, subcategory):
                appeared[subcategory].add(positions[key])

        latest_position = len(exam_keys) - 1
        gaps = {}
        for subcategory, indexes in appeared.items():
            last_seen = max(indexes)
            gaps[subcategory] = {
                "gap": max(latest_position - last_seen, 0),
                "last_seen": self._format_exam_key(exam_keys[last_seen]),
                "total_count": len(indexes),
            }
        return {
            "exam_keys": [self._format_exam_key(key) for key in exam_keys],
            "gaps": gaps,
            "buckets": self._buckets(gaps),
        }

    def save(self, analysis: dict[str, Any]) -> Path:
        """공백 분석 결과를 JSON으로 저장합니다."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.output_path

    def format_report(self, analysis: dict[str, Any]) -> str:
        """공백 분석 결과를 GUI 출력용 문자열로 변환합니다."""
        gaps = analysis.get("gaps", {})
        if not gaps:
            return "출제 공백 분석\n- 데이터 없음"
        lines = ["출제 공백 분석"]
        for bucket, items in analysis.get("buckets", {}).items():
            if items:
                lines.append(f"- 최근 미출제 {bucket}: {', '.join(items[:10])}")
        lines.append("\n공백 상위 유형")
        ordered = sorted(gaps.items(), key=lambda item: item[1]["gap"], reverse=True)
        for subcategory, info in ordered[:15]:
            lines.append(f"- {subcategory}: 최근 {info['gap']}회 미출제 / 마지막 출제 {info['last_seen']}")
        return "\n".join(lines)

    def gap_scores(self, analysis: dict[str, Any]) -> dict[str, int]:
        """우선순위 계산용 공백 점수를 반환합니다."""
        return {subcategory: int(info.get("gap") or 0) for subcategory, info in analysis.get("gaps", {}).items()}

    def _exam_keys(self, records: list[dict[str, Any]]) -> list[tuple[int, int]]:
        return sorted({(int(record.get("year") or 0), int(record.get("round") or 0)) for record in records if record.get("year") and record.get("round")})

    def _format_exam_key(self, key: tuple[int, int]) -> str:
        return f"{key[0]}-{key[1]}"

    def _buckets(self, gaps: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
        buckets: dict[str, list[str]] = {"1회": [], "2회": [], "3회": [], "4회": [], "5회 이상": []}
        for subcategory, info in gaps.items():
            gap = int(info.get("gap") or 0)
            if gap <= 0:
                continue
            key = "5회 이상" if gap >= 5 else f"{gap}회"
            buckets[key].append(subcategory)
        for values in buckets.values():
            values.sort()
        return buckets

    def _is_unclassified(self, record: dict[str, Any], subcategory: str) -> bool:
        return str(record.get("category") or "") == "미분류" or subcategory == "미분류"
