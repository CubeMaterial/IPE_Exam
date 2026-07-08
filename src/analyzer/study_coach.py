"""시험일까지의 학습 우선순위와 추천 계획을 계산합니다."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any


class StudyCoach:
    """Python 계산 결과를 바탕으로 오늘 공부와 로드맵 후보를 생성합니다."""

    IMPORTANCE = {
        "포인터": 5,
        "JOIN": 5,
        "GROUP BY": 5,
        "프로세스": 4,
        "TCP/IP": 4,
        "OSI 7계층": 4,
        "정규화": 4,
        "SQL Injection": 4,
        "상속": 3,
        "리스트": 3,
    }

    def priorities(self, records: list[dict[str, Any]], gap_scores: dict[str, int] | None = None) -> list[dict[str, Any]]:
        """빈도, 최근성, 반복성, 연관개념, 중요도로 학습 점수를 계산합니다."""
        classified_records = [
            record for record in records
            if not self._is_unclassified(record, self._primary(record))
        ]
        counts = Counter(self._primary(record) for record in classified_records)
        counts.pop("", None)
        by_subcategory_year: dict[str, set[int]] = defaultdict(set)
        related_count: Counter = Counter()
        latest_year = max([int(record.get("year") or 0) for record in classified_records] or [0])
        recent_counts: Counter = Counter()
        for record in classified_records:
            subcategory = self._primary(record)
            year = int(record.get("year") or 0)
            if not subcategory or self._is_unclassified(record, subcategory):
                continue
            by_subcategory_year[subcategory].add(year)
            concepts = record.get("concepts") if isinstance(record.get("concepts"), list) else []
            secondary = record.get("secondary") if isinstance(record.get("secondary"), list) else []
            intent = record.get("intent") if isinstance(record.get("intent"), list) else []
            mistakes = record.get("mistakes") if isinstance(record.get("mistakes"), list) else []
            related_items = {str(item) for item in [*secondary, *concepts, *intent, *mistakes] if item and item != subcategory}
            related_count[subcategory] += len(related_items)
            if latest_year and year >= latest_year - 2:
                recent_counts[subcategory] += 1

        results = []
        for subcategory, frequency in counts.items():
            gap_score = (gap_scores or {}).get(subcategory, 0)
            recent_score = recent_counts[subcategory]
            repeat_score = len(by_subcategory_year[subcategory])
            relation_score = min(related_count[subcategory], 5)
            importance_score = self.IMPORTANCE.get(subcategory, 2)
            score = frequency * 0.4 + recent_score * 0.2 + gap_score * 0.2 + relation_score * 0.1 + importance_score * 0.1
            results.append(
                {
                    "subcategory": subcategory,
                    "score": round(score, 2),
                    "stars": self._stars(score),
                    "frequency": frequency,
                    "recent": recent_counts[subcategory],
                    "gap": gap_score,
                    "related": related_count[subcategory],
                }
            )
        return sorted(results, key=lambda item: item["score"], reverse=True)

    def _is_unclassified(self, record: dict[str, Any], subcategory: str) -> bool:
        return str(record.get("category") or "") == "미분류" or subcategory == "미분류"

    def _primary(self, record: dict[str, Any]) -> str:
        return str(record.get("primary") or record.get("subcategory") or record.get("sub_category") or "")

    def today(
        self,
        records: list[dict[str, Any]],
        exam_date: date,
        today: date | None = None,
        hours: float = 2.5,
        gap_scores: dict[str, int] | None = None,
    ) -> str:
        """오늘 공부 추천 문구를 생성합니다."""
        current = today or date.today()
        d_day = (exam_date - current).days
        priorities = self.priorities(records, gap_scores=gap_scores)[:5]
        lines = [f"오늘 공부 추천", f"시험일까지 D-{d_day}", ""]
        if not priorities:
            lines.append("- 기출 데이터가 없습니다.")
            return "\n".join(lines)
        for index, item in enumerate(priorities, start=1):
            lines.append(
                f"{index}. {item['subcategory']} {item['stars']}\n"
                f"   출제 {item['frequency']}회, 최근 출제 {item['recent']}회, 출제 공백 {item['gap']}회, 연관 개념 {item['related']}개"
            )
        lines.append(f"\n오늘 공부 예상 시간: {hours:g}시간")
        return "\n".join(lines)

    def roadmap(
        self,
        records: list[dict[str, Any]],
        exam_date: date,
        today: date | None = None,
        hours_per_day: float = 2.5,
        gap_scores: dict[str, int] | None = None,
    ) -> str:
        """시험일까지 우선순위 기반 학습 로드맵을 생성합니다."""
        current = today or date.today()
        days = max((exam_date - current).days, 1)
        priorities = self.priorities(records, gap_scores=gap_scores)
        if not priorities:
            return "학습 로드맵\n- 기출 데이터가 없습니다."
        topics_per_day = 2 if hours_per_day < 3 else 3
        lines = ["학습 로드맵"]
        day = current
        index = 0
        for offset in range(min(days, 30)):
            topics = []
            for _ in range(topics_per_day):
                topics.append(priorities[index % len(priorities)]["subcategory"])
                index += 1
            lines.append(f"- D-{days - offset} ({day.isoformat()}): {', '.join(topics)}")
            day += timedelta(days=1)
        return "\n".join(lines)

    def wrong_answer_report(self, records: list[dict[str, Any]], wrong_text: str) -> str:
        """사용자가 적은 오답 키워드와 가까운 학습 주제를 추천합니다."""
        query = wrong_text.lower()
        matched = []
        for item in self.priorities(records):
            if item["subcategory"].lower() in query:
                matched.append(item)
        if not matched:
            return "오답 분석\n- 입력한 오답 키워드와 직접 일치하는 기출 세부유형을 찾지 못했습니다."
        lines = ["오답 분석"]
        for item in matched[:10]:
            lines.append(f"- {item['subcategory']}: {item['stars']} / 관련 기출 {item['frequency']}회 우선 복습")
        return "\n".join(lines)

    def _stars(self, score: int) -> str:
        if score >= 5:
            return "★★★★★"
        if score >= 4:
            return "★★★★☆"
        if score >= 3:
            return "★★★☆☆"
        if score >= 2:
            return "★★☆☆☆"
        return "★☆☆☆☆"
