"""문제 세부 유형 간 연관 개념 그룹을 분석합니다."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from config.config import CONFIG


class RelationAnalyzer:
    """세부 유형을 시험 대비 개념군으로 묶습니다."""

    GROUP_RULES = {
        "포인터 계열": ("포인터", "배열", "문자열", "구조체"),
        "SQL 집계/조인 계열": ("JOIN", "INNER JOIN", "OUTER JOIN", "GROUP BY", "HAVING", "집계함수", "SUBQUERY"),
        "운영체제 계열": ("프로세스", "스레드", "교착상태", "운영체제", "스케줄링"),
        "네트워크 계열": ("TCP", "UDP", "TCP/IP", "OSI 7계층", "HTTP", "DNS", "라우팅"),
        "보안 계열": ("SQL Injection", "XSS", "CSRF", "Buffer Overflow", "AES", "RSA", "SHA"),
        "Java 객체지향 계열": ("상속", "오버라이딩", "클래스", "인터페이스", "추상클래스"),
        "Python 자료구조 계열": ("리스트", "슬라이싱", "딕셔너리", "튜플", "Set", "Lambda"),
    }

    def __init__(self, output_path: Path | None = None) -> None:
        """연관 그래프 저장 경로를 초기화합니다."""
        self.output_path = output_path or CONFIG.exam_index_dir / "relation_graph.json"

    def analyze(self, records: list[dict[str, Any]]) -> dict[str, Counter]:
        """같은 문제/분류 축을 기준으로 연관 개념 빈도를 계산합니다."""
        groups: dict[str, Counter] = {name: Counter() for name in self.GROUP_RULES}
        category_groups: dict[str, Counter] = {}
        subcategory_groups: dict[str, Counter] = {}
        for record in records:
            subcategory = str(record.get("primary") or record.get("subcategory") or record.get("sub_category") or "")
            if self._is_unclassified(record, subcategory):
                continue
            concepts = [str(item) for item in record.get("concepts", [])] if isinstance(record.get("concepts"), list) else []
            secondary = [str(item) for item in record.get("secondary", [])] if isinstance(record.get("secondary"), list) else []
            intent = [str(item) for item in record.get("intent", [])] if isinstance(record.get("intent"), list) else []
            mistakes = [str(item) for item in record.get("mistakes", [])] if isinstance(record.get("mistakes"), list) else []
            category = str(record.get("category") or "")
            subject = str(record.get("subject") or "")
            haystack = " ".join([subject, category, subcategory, *secondary, *concepts, *intent, *mistakes])
            for group, keywords in self.GROUP_RULES.items():
                if any(keyword in haystack for keyword in keywords):
                    groups[group][subcategory or "미분류"] += 1
            if category:
                category_groups.setdefault(f"{category} 연관", Counter())
                category_groups[f"{category} 연관"].update(item for item in [subcategory, *secondary, *concepts, *intent, *mistakes] if item)
            if subcategory:
                subcategory_groups.setdefault(f"{subcategory} 연관", Counter())
                subcategory_groups[f"{subcategory} 연관"].update(item for item in [*secondary, *concepts, *intent, *mistakes] if item and item != subcategory)
        merged = groups | category_groups | subcategory_groups
        return {group: counter for group, counter in merged.items() if counter}

    def graph(self, groups: dict[str, Counter]) -> dict[str, Any]:
        """연관 개념군을 노드/엣지 구조로 변환합니다."""
        nodes = []
        edges = []
        for group, counter in groups.items():
            nodes.append({"id": group, "type": "group", "count": sum(counter.values())})
            for subcategory, count in counter.items():
                nodes.append({"id": subcategory, "type": "subcategory", "count": count})
                edges.append({"source": group, "target": subcategory, "weight": count})
        return {"nodes": nodes, "edges": edges}

    def save_graph(self, groups: dict[str, Counter]) -> Path:
        """Relation Graph를 JSON 파일로 저장합니다."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.output_path.write_text(json.dumps(self.graph(groups), ensure_ascii=False, indent=2), encoding="utf-8")
        return self.output_path

    def format_report(self, groups: dict[str, Counter]) -> str:
        """연관 개념 분석을 문자열로 변환합니다."""
        if not groups:
            return "⑥ 연관 개념\n- 데이터 없음"
        lines = ["⑥ 연관 개념"]
        for group, counter in groups.items():
            details = ", ".join(f"{name}({count})" for name, count in counter.most_common(8))
            lines.append(f"- {group}: {details}")
        return "\n".join(lines)

    def _is_unclassified(self, record: dict[str, Any], subcategory: str) -> bool:
        return (
            str(record.get("category") or "") == "미분류"
            or subcategory == "미분류"
            or not subcategory
        )
