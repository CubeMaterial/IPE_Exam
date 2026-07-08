"""세부유형의 연도/회차 흐름을 계산합니다."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from config.config import CONFIG


class FlowAnalyzer:
    """동일 세부유형 반복과 회차 간 이어지는 개념 흐름을 계산합니다."""

    def __init__(self, output_path: Path | None = None) -> None:
        """흐름 분석 저장 경로를 초기화합니다."""
        self.output_path = output_path or CONFIG.exam_index_dir / "exam_flow.json"

    def analyze(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """출제 흐름 데이터를 반환합니다."""
        subcategory_timeline: dict[str, list[dict[str, int]]] = defaultdict(list)
        exam_sequence: dict[tuple[int, int], list[str]] = defaultdict(list)
        all_exam_keys = sorted({(int(record.get("year") or 0), int(record.get("round") or 0)) for record in records if record.get("year") and record.get("round")})
        for record in sorted(records, key=lambda item: (int(item.get("year") or 0), int(item.get("round") or 0), int(item.get("question_number") or 0))):
            subcategory = str(record.get("subcategory") or record.get("sub_category") or "")
            if self._is_unclassified(record, subcategory):
                continue
            year = int(record.get("year") or 0)
            round_number = int(record.get("round") or 0)
            if not subcategory or not year:
                continue
            subcategory_timeline[subcategory].append(
                {
                    "year": year,
                    "round": round_number,
                    "question_number": int(record.get("question_number") or 0),
                }
            )
            exam_sequence[(year, round_number)].append(subcategory)

        recent_exams = sorted(all_exam_keys, reverse=True)[:7]
        recent_exam_counts: Counter = Counter()
        recent_question_counts: Counter = Counter()
        recent_exam_labels: dict[str, list[str]] = defaultdict(list)
        for key in recent_exams:
            values = exam_sequence[key]
            label = f"{key[0]}-{key[1]}"
            for subcategory in set(values):
                recent_exam_counts[subcategory] += 1
                recent_exam_labels[subcategory].append(label)
            recent_question_counts.update(values)
        return {
            "subcategory_timeline": dict(subcategory_timeline),
            "recent_exam_count": len(recent_exams),
            "recent_exam_counts": recent_exam_counts,
            "recent_question_counts": recent_question_counts,
            "recent_exam_labels": dict(recent_exam_labels),
        }

    def save(self, analysis: dict[str, Any]) -> Path:
        """흐름 분석 결과를 JSON으로 저장합니다."""
        serializable = analysis | {
            "recent_exam_counts": dict(analysis.get("recent_exam_counts", {})),
            "recent_question_counts": dict(analysis.get("recent_question_counts", {})),
        }
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.output_path

    def format_report(self, analysis: dict[str, Any]) -> str:
        """출제 흐름을 GUI 출력용 문자열로 변환합니다."""
        if not analysis.get("subcategory_timeline"):
            return "출제 흐름\n- 데이터 없음"
        lines = ["출제 흐름"]
        recent_exam_count = analysis.get("recent_exam_count", 0)
        for subcategory, count in analysis.get("recent_exam_counts", Counter()).most_common(12):
            timeline = analysis["subcategory_timeline"].get(subcategory, [])
            all_exams = sorted({f"{item['year']}-{item['round']}" for item in timeline})
            exam_text = " → ".join(all_exams[-12:])
            question_count = len(timeline)
            lines.append(
                f"- {subcategory}: 최근 {recent_exam_count}회 중 {count}회차 출제 / "
                f"총 {question_count}문항 / 출제 회차: {exam_text}"
            )
        return "\n".join(lines)

    def _is_unclassified(self, record: dict[str, Any], subcategory: str) -> bool:
        return (
            str(record.get("category") or "") == "미분류"
            or subcategory == "미분류"
            or not subcategory
        )
