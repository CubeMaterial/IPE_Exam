"""기출 기반 출제 가능성 점수를 계산합니다."""

from __future__ import annotations

from collections import Counter
from typing import Any


class PredictionAnalyzer:
    """빈도, 공백, 안정도, 클러스터, 최근 증가로 Prediction Score를 계산합니다."""

    def analyze(
        self,
        records: list[dict[str, Any]],
        gap_scores: dict[str, int],
        stability_scores: dict[str, float],
        cluster_scores: dict[str, float],
        recent_change: Counter,
    ) -> list[dict[str, Any]]:
        """출제 가능성 점수 목록을 반환합니다."""
        filtered = [
            record for record in records
            if str(record.get("category") or "") != "미분류"
            and str(record.get("primary") or record.get("subcategory") or "") != "미분류"
        ]
        counts = Counter(str(record.get("primary") or record.get("subcategory") or "") for record in filtered)
        max_frequency = max(counts.values() or [1])
        max_gap = max(gap_scores.values() or [1])
        max_recent = max(recent_change.values() or [1])
        results = []
        for concept, frequency in counts.items():
            frequency_score = frequency / max_frequency
            gap_score = gap_scores.get(concept, 0) / max_gap if max_gap else 0
            stability_score = stability_scores.get(concept, 0)
            cluster_score = cluster_scores.get(concept, 0)
            recent_score = recent_change.get(concept, 0) / max_recent if max_recent else 0
            score = (
                frequency_score * 0.3
                + gap_score * 0.2
                + stability_score * 0.2
                + cluster_score * 0.2
                + recent_score * 0.1
            )
            results.append(
                {
                    "concept": concept,
                    "score": round(score * 100, 2),
                    "stars": self._stars(score),
                    "frequency": frequency,
                    "gap": gap_scores.get(concept, 0),
                }
            )
        return sorted(results, key=lambda item: item["score"], reverse=True)

    def format_report(self, predictions: list[dict[str, Any]]) -> str:
        """출제 가능성 분석 결과를 문자열로 변환합니다."""
        if not predictions:
            return "출제 가능성\n- 데이터 없음"
        lines = ["출제 가능성", "기출 기반 가능성 점수입니다. 반드시 출제된다는 의미는 아닙니다."]
        for item in predictions[:20]:
            lines.append(
                f"- {item['concept']}: {item['score']}점 {item['stars']} / "
                f"빈도 {item['frequency']}회, 공백 {item['gap']}회"
            )
        return "\n".join(lines)

    def _stars(self, score: float) -> str:
        if score >= 0.8:
            return "★★★★★"
        if score >= 0.65:
            return "★★★★☆"
        if score >= 0.5:
            return "★★★☆☆"
        if score >= 0.3:
            return "★★☆☆☆"
        return "★☆☆☆☆"
