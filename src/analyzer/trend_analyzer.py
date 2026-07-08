"""출제 흐름을 Python 통계 결과와 구조화 레코드로 분석합니다."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


class TrendAnalyzer:
    """세부 유형의 연도별 반복과 동반 출제 흐름을 계산합니다."""

    def analyze(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """출제 흐름 분석 데이터를 반환합니다."""
        by_year: dict[int, list[str]] = defaultdict(list)
        for record in records:
            year = int(record.get("year") or 0)
            subcategory = str(record.get("subcategory") or record.get("sub_category") or "")
            if str(record.get("category") or "") == "미분류" or subcategory == "미분류":
                continue
            if year and subcategory:
                by_year[year].append(subcategory)

        flow = {year: Counter(values).most_common(5) for year, values in sorted(by_year.items())}
        total = Counter(item for values in by_year.values() for item in values)
        recent_years = sorted(by_year.keys(), reverse=True)[:7]
        recent_values = [item for year in recent_years for item in by_year[year]]
        recent = Counter(recent_values)
        co_occurrence = self._co_occurrence(records)
        recommendations = {
            item: self._stars(count, len(recent_years))
            for item, count in recent.most_common(20)
        }
        return {
            "flow": flow,
            "total": total,
            "recent": recent,
            "co_occurrence": co_occurrence,
            "recommendations": recommendations,
        }

    def format_report(self, analysis: dict[str, Any]) -> str:
        """출제 흐름 분석을 문자열로 변환합니다."""
        lines = ["⑤ 출제 흐름"]
        for year, items in analysis["flow"].items():
            joined = ", ".join(f"{name}({count})" for name, count in items)
            lines.append(f"- {year}: {joined or '데이터 없음'}")
        lines.append("\n공부 우선순위")
        for item, stars in list(analysis["recommendations"].items())[:15]:
            count = analysis["recent"][item]
            lines.append(f"- {item}: 최근 흐름 {count}회 / 추천 학습 {stars}")
        return "\n".join(lines)

    def _co_occurrence(self, records: list[dict[str, Any]]) -> dict[str, Counter]:
        grouped: dict[tuple[int, int], set[str]] = defaultdict(set)
        for record in records:
            key = (int(record.get("year") or 0), int(record.get("round") or 0))
            subcategory = str(record.get("subcategory") or record.get("sub_category") or "")
            if key[0] and key[1] and subcategory and str(record.get("category") or "") != "미분류" and subcategory != "미분류":
                grouped[key].add(subcategory)
        relations: dict[str, Counter] = defaultdict(Counter)
        for items in grouped.values():
            for source in items:
                for target in items:
                    if source != target:
                        relations[source][target] += 1
        return dict(relations)

    def _stars(self, count: int, recent_year_count: int) -> str:
        if recent_year_count <= 0:
            return "★"
        ratio = count / max(recent_year_count, 1)
        if ratio >= 0.6:
            return "★★★★★"
        if ratio >= 0.4:
            return "★★★★"
        if ratio >= 0.25:
            return "★★★"
        if ratio >= 0.1:
            return "★★"
        return "★"
