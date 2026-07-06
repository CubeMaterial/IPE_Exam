"""과년도 기출문제 출제 빈도 분석 기능을 제공합니다."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


class FrequencyAnalyzer:
    """기출문제 JSON 인덱스를 기준으로 출제 빈도를 계산합니다."""

    def analyze(self, records: list[dict[str, Any]], basis: str = "전체", value: str = "") -> dict[str, Any]:
        """선택 기준에 맞게 기출 빈도를 분석합니다."""
        filtered = self._filter_records(records, basis, value)
        recent_records = self._recent_year_records(filtered, 3)
        older_records = [record for record in filtered if record not in recent_records]
        return {
            "total_count": len(filtered),
            "year_category": self._count_by(filtered, "year", "category"),
            "round_category": self._count_by(filtered, "round", "category"),
            "sub_category": Counter(record.get("sub_category", "") for record in filtered if record.get("sub_category")),
            "question_type": Counter(record.get("question_type", "") for record in filtered if record.get("question_type")),
            "language": Counter(record.get("language", "") for record in filtered if record.get("language")),
            "recent_increased": self._trend(recent_records, older_records, "sub_category", increased=True),
            "recent_decreased": self._trend(recent_records, older_records, "sub_category", increased=False),
            "repeated_types": self._repeated(filtered),
            "comeback_candidates": self._comeback_candidates(filtered),
        }

    def format_report(self, analysis: dict[str, Any]) -> str:
        """빈도 분석 결과를 화면 출력용 문자열로 변환합니다."""
        return "\n".join(
            [
                f"분석 문제 수: {analysis['total_count']}",
                "\n세부 유형별 출제 빈도:",
                self._format_counter(analysis["sub_category"]),
                "\n문제 유형별 출제 빈도:",
                self._format_counter(analysis["question_type"]),
                "\n언어별 출제 빈도:",
                self._format_counter(analysis["language"]),
                "\n최근 3개년 증가 유형:",
                self._format_counter(analysis["recent_increased"]),
                "\n최근 3개년 감소 유형:",
                self._format_counter(analysis["recent_decreased"]),
                "\n반복 출제 유형:",
                self._format_counter(analysis["repeated_types"]),
                "\n한동안 안 나왔지만 다시 나올 수 있는 유형:",
                self._format_counter(analysis["comeback_candidates"]),
            ]
        )

    def _filter_records(self, records: list[dict[str, Any]], basis: str, value: str) -> list[dict[str, Any]]:
        """분석 기준에 맞는 레코드만 필터링합니다."""
        if basis == "최근 3개년":
            return self._recent_year_records(records, 3)
        if basis == "특정 연도" and value:
            return [record for record in records if str(record.get("year")) == str(value)]
        if basis == "특정 과목" and value:
            return [record for record in records if record.get("category") == value]
        return records

    def _count_by(self, records: list[dict[str, Any]], first_key: str, second_key: str) -> dict[Any, Counter]:
        """두 기준을 묶어 빈도를 계산합니다."""
        grouped: dict[Any, Counter] = defaultdict(Counter)
        for record in records:
            grouped[record.get(first_key)][record.get(second_key, "")] += 1
        return dict(grouped)

    def _recent_year_records(self, records: list[dict[str, Any]], years: int) -> list[dict[str, Any]]:
        """최근 N개년 레코드를 반환합니다."""
        year_values = sorted({int(record.get("year")) for record in records if record.get("year")}, reverse=True)
        target_years = set(year_values[:years])
        return [record for record in records if int(record.get("year", 0)) in target_years]

    def _trend(
        self,
        recent_records: list[dict[str, Any]],
        older_records: list[dict[str, Any]],
        key: str,
        increased: bool,
    ) -> Counter:
        """최근 레코드와 이전 레코드의 출제 경향 차이를 계산합니다."""
        recent = Counter(record.get(key, "") for record in recent_records if record.get(key))
        older = Counter(record.get(key, "") for record in older_records if record.get(key))
        scores = Counter()
        for item in set(recent) | set(older):
            diff = recent[item] - older[item]
            if (increased and diff > 0) or (not increased and diff < 0):
                scores[item] = abs(diff)
        return scores

    def _repeated(self, records: list[dict[str, Any]]) -> Counter:
        """두 번 이상 등장한 세부 유형을 계산합니다."""
        counts = Counter(record.get("sub_category", "") for record in records if record.get("sub_category"))
        return Counter({key: value for key, value in counts.items() if value >= 2})

    def _comeback_candidates(self, records: list[dict[str, Any]]) -> Counter:
        """최근에는 적지만 과거에 반복된 세부 유형을 계산합니다."""
        recent = Counter(record.get("sub_category", "") for record in self._recent_year_records(records, 3))
        total = Counter(record.get("sub_category", "") for record in records if record.get("sub_category"))
        return Counter({key: value for key, value in total.items() if value >= 2 and recent.get(key, 0) == 0})

    def _format_counter(self, counter: Counter) -> str:
        """Counter를 순위 문자열로 변환합니다."""
        if not counter:
            return "- 데이터 없음"
        return "\n".join(f"- {key}: {value}" for key, value in counter.most_common(20))
