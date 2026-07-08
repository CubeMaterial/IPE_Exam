"""출제 Tree 기준 학습 커버리지를 계산합니다."""

from __future__ import annotations

from typing import Any


class CoverageAnalyzer:
    """사용자가 공부 완료한 세부유형이 출제 Tree를 얼마나 덮는지 계산합니다."""

    def analyze(self, tree: dict[str, Any], completed_topics: set[str]) -> dict[str, Any]:
        """전체 및 과목별 학습 커버리지를 계산합니다."""
        subject_results = {}
        total = 0
        completed = 0
        for subject, subject_node in tree.items():
            subject_topics = set()
            for category_node in subject_node.get("categories", {}).values():
                subject_topics.update(category_node.get("subcategories", {}).keys())
            subject_completed = len(subject_topics & completed_topics)
            subject_total = len(subject_topics)
            total += subject_total
            completed += subject_completed
            subject_results[subject] = {
                "total": subject_total,
                "completed": subject_completed,
                "coverage": self._percent(subject_completed, subject_total),
            }
        return {
            "total": total,
            "completed": completed,
            "coverage": self._percent(completed, total),
            "subjects": subject_results,
        }

    def format_report(self, analysis: dict[str, Any]) -> str:
        """커버리지 분석 결과를 GUI 출력용 문자열로 변환합니다."""
        lines = [
            "출제 커버리지",
            f"- 전체: {analysis['completed']} / {analysis['total']} ({analysis['coverage']}%)",
        ]
        for subject, info in analysis.get("subjects", {}).items():
            lines.append(f"- {subject}: {info['completed']} / {info['total']} ({info['coverage']}%)")
        return "\n".join(lines)

    def _percent(self, completed: int, total: int) -> int:
        return int(round(completed / total * 100)) if total else 0
