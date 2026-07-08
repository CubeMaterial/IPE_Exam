"""세부유형별 출제 주기를 계산합니다."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from config.config import CONFIG


class CycleAnalyzer:
    """연도-회차 순서에서 같은 SubCategory의 평균 출제 간격을 계산합니다."""

    def __init__(self, output_path: Path | None = None) -> None:
        """주기 분석 저장 경로를 초기화합니다."""
        self.output_path = output_path or CONFIG.exam_index_dir / "exam_cycle.json"

    def analyze(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """세부유형별 평균 출제 주기를 계산합니다."""
        exam_keys = sorted({(int(record.get("year") or 0), int(record.get("round") or 0)) for record in records if record.get("year") and record.get("round")})
        positions = {key: index for index, key in enumerate(exam_keys)}
        timelines: dict[str, list[int]] = defaultdict(list)
        labels = {index: f"{key[0]}-{key[1]}" for key, index in positions.items()}
        for record in records:
            key = (int(record.get("year") or 0), int(record.get("round") or 0))
            subcategory = str(record.get("subcategory") or record.get("sub_category") or "")
            if key in positions and subcategory and not self._is_unclassified(record, subcategory):
                timelines[subcategory].append(positions[key])

        cycles = {}
        for subcategory, indexes in timelines.items():
            unique_indexes = sorted(set(indexes))
            intervals = [current - previous for previous, current in zip(unique_indexes, unique_indexes[1:], strict=False)]
            cycles[subcategory] = {
                "timeline": [labels[index] for index in unique_indexes],
                "intervals": intervals,
                "average_cycle": round(mean(intervals), 2) if intervals else None,
            }
        return {"cycles": cycles}

    def save(self, analysis: dict[str, Any]) -> Path:
        """주기 분석 결과를 JSON으로 저장합니다."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.output_path

    def format_report(self, analysis: dict[str, Any]) -> str:
        """주기 분석 결과를 GUI 출력용 문자열로 변환합니다."""
        cycles = analysis.get("cycles", {})
        if not cycles:
            return "출제 주기 분석\n- 데이터 없음"
        lines = ["출제 주기 분석"]
        ordered = sorted(
            cycles.items(),
            key=lambda item: item[1]["average_cycle"] if item[1]["average_cycle"] is not None else 999,
        )
        for subcategory, info in ordered[:15]:
            cycle = info["average_cycle"]
            cycle_text = f"평균 {cycle}회 주기" if cycle is not None else "반복 출제 데이터 부족"
            lines.append(f"- {subcategory}: {cycle_text} / {' → '.join(info['timeline'][-8:])}")
        return "\n".join(lines)

    def _is_unclassified(self, record: dict[str, Any], subcategory: str) -> bool:
        return str(record.get("category") or "") == "미분류" or subcategory == "미분류"
