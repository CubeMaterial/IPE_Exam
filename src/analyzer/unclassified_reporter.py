"""분류 실패 문항을 별도 섹션으로 정리합니다."""

from __future__ import annotations

from typing import Any


class UnclassifiedReporter:
    """미분류 문항을 분석 대상에서 분리해 재분류 목록으로 출력합니다."""

    def collect(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """category/subcategory가 미분류인 문항만 반환합니다."""
        items = []
        for record in records:
            category = str(record.get("category") or "")
            subcategory = str(record.get("subcategory") or record.get("sub_category") or "")
            if category != "미분류" and subcategory != "미분류":
                continue
            items.append(
                {
                    "year": record.get("year", ""),
                    "round": record.get("round", ""),
                    "question_number": record.get("question_number", ""),
                    "body_preview": self._preview(str(record.get("body") or "")),
                    "subject": record.get("subject", ""),
                    "category": category,
                    "subcategory": subcategory,
                    "needs_reclassification": True,
                }
            )
        return items

    def format_report(self, records: list[dict[str, Any]]) -> str:
        """분류 실패 문항 섹션을 생성합니다."""
        items = self.collect(records)
        lines = ["분류 실패 문항"]
        if not items:
            lines.append("- 없음")
            return "\n".join(lines)
        for item in items:
            lines.append(
                f"- {item['year']}년 {item['round']}회 {item['question_number']}번\n"
                f"  문제 일부: {item['body_preview']}\n"
                f"  현재 분류: subject={item['subject']} / category={item['category']} / subcategory={item['subcategory']}\n"
                f"  재분류 필요 여부: {'예' if item['needs_reclassification'] else '아니오'}"
            )
        return "\n".join(lines)

    def _preview(self, text: str, limit: int = 120) -> str:
        collapsed = " ".join(text.split())
        return collapsed[:limit] + ("..." if len(collapsed) > limit else "")
