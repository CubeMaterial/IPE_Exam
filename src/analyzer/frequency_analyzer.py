"""과년도 기출문제 출제 빈도 분석 기능을 제공합니다."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


class FrequencyAnalyzer:
    """기출문제 JSON 인덱스를 기준으로 출제 빈도를 계산합니다."""

    def analyze(
        self,
        records: list[dict[str, Any]],
        basis: str = "전체",
        value: str = "",
        category: str = "",
    ) -> dict[str, Any]:
        """선택 기준에 맞게 기출 빈도를 분석합니다."""
        filtered = self._filter_records(records, basis, value, category)
        recent_records = self._recent_year_records(filtered, 3)
        older_records = [record for record in filtered if record not in recent_records]
        return {
            "total_count": len(filtered),
            "year_category": self._count_by(filtered, "year", "subject"),
            "round_category": self._count_by(filtered, "round", "subject"),
            "sub_category": Counter(self._subcategory(record) for record in filtered if self._subcategory(record)),
            "question_type": Counter(record.get("question_type", "") for record in filtered if record.get("question_type")),
            "language": Counter(record.get("language", "") for record in filtered if record.get("language")),
            "recent_increased": self._trend(recent_records, older_records, "subcategory", increased=True),
            "recent_decreased": self._trend(recent_records, older_records, "subcategory", increased=False),
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

    def _filter_records(
        self,
        records: list[dict[str, Any]],
        basis: str,
        value: str,
        category: str = "",
    ) -> list[dict[str, Any]]:
        """분석 기준에 맞는 레코드만 필터링합니다."""
        filtered = records
        if basis == "최근 3개년":
            filtered = self._recent_year_records(filtered, 3)
        elif basis == "특정 연도" and value:
            filtered = [record for record in filtered if str(record.get("year")) == str(value)]
        if category:
            filtered = [record for record in filtered if self._subject(record) == category]
        return filtered

    def _count_by(self, records: list[dict[str, Any]], first_key: str, second_key: str) -> dict[Any, Counter]:
        """두 기준을 묶어 빈도를 계산합니다."""
        grouped: dict[Any, Counter] = defaultdict(Counter)
        for record in records:
            value = self._subject(record) if second_key == "subject" else record.get(second_key, "")
            grouped[record.get(first_key)][value] += 1
        return dict(grouped)

    def _recent_year_records(self, records: list[dict[str, Any]], years: int) -> list[dict[str, Any]]:
        """최근 N개년 레코드를 반환합니다."""
        year_values = sorted({self._to_year(record.get("year")) for record in records if self._to_year(record.get("year"))}, reverse=True)
        target_years = set(year_values[:years])
        return [record for record in records if self._to_year(record.get("year")) in target_years]

    def _to_year(self, value: Any) -> int:
        """레코드의 연도 값을 안전하게 정수로 변환합니다."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _trend(
        self,
        recent_records: list[dict[str, Any]],
        older_records: list[dict[str, Any]],
        key: str,
        increased: bool,
    ) -> Counter:
        """최근 레코드와 이전 레코드의 출제 경향 차이를 계산합니다."""
        recent = Counter(self._record_value(record, key) for record in recent_records if self._record_value(record, key))
        older = Counter(self._record_value(record, key) for record in older_records if self._record_value(record, key))
        scores = Counter()
        for item in set(recent) | set(older):
            diff = recent[item] - older[item]
            if (increased and diff > 0) or (not increased and diff < 0):
                scores[item] = abs(diff)
        return scores

    def _repeated(self, records: list[dict[str, Any]]) -> Counter:
        """두 번 이상 등장한 세부 유형을 계산합니다."""
        counts = Counter(self._subcategory(record) for record in records if self._subcategory(record))
        return Counter({key: value for key, value in counts.items() if value >= 2})

    def _comeback_candidates(self, records: list[dict[str, Any]]) -> Counter:
        """최근에는 적지만 과거에 반복된 세부 유형을 계산합니다."""
        recent = Counter(self._subcategory(record) for record in self._recent_year_records(records, 3) if self._subcategory(record))
        total = Counter(self._subcategory(record) for record in records if self._subcategory(record))
        return Counter({key: value for key, value in total.items() if value >= 2 and recent.get(key, 0) == 0})

    def _subject(self, record: dict[str, Any]) -> str:
        """새 subject 필드와 기존 category 필드를 호환 처리합니다."""
        return str(record.get("subject") or record.get("category") or "")

    def _subcategory(self, record: dict[str, Any]) -> str:
        """새 subcategory 필드와 기존 sub_category 필드를 호환 처리합니다."""
        return str(record.get("subcategory") or record.get("sub_category") or "")

    def _record_value(self, record: dict[str, Any], key: str) -> str:
        """호환 키를 고려해 분석 값을 가져옵니다."""
        if key == "subject":
            return self._subject(record)
        if key == "subcategory":
            return self._subcategory(record)
        return str(record.get(key, "") or "")

    def _format_counter(self, counter: Counter) -> str:
        """Counter를 순위 문자열로 변환합니다."""
        if not counter:
            return "- 데이터 없음"
        return "\n".join(f"- {key}: {value}" for key, value in counter.most_common(20))
