"""Concept Dictionary와 기출 동시 출현 기반 Topic Cluster를 생성합니다."""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from typing import Any


class TopicClusterAnalyzer:
    """NetworkX 그래프로 관련 개념 클러스터를 계산합니다."""

    PREDEFINED_CLUSTERS = {
        "C 클러스터": ["포인터", "배열", "문자열", "구조체", "함수", "반복문", "증감연산"],
        "Java 클러스터": ["클래스", "상속", "오버라이딩", "static", "인터페이스", "예외처리", "컬렉션"],
        "Python 클러스터": ["리스트", "슬라이싱", "딕셔너리", "튜플", "Set", "Range"],
        "SQL 클러스터": ["SELECT", "JOIN", "GROUP BY", "HAVING", "집계함수", "DML", "DDL", "INDEX", "제약조건"],
        "네트워크 클러스터": ["TCP/IP", "TCP", "UDP", "OSI", "DNS", "ARP", "ICMP", "라우팅"],
        "보안 클러스터": ["SQL Injection", "XSS", "CSRF", "AES", "RSA", "SHA", "ISMS", "인증", "접근통제"],
    }

    def analyze(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """정의된 영역별 클러스터 안에서 문제 단위 동시 출현 그래프를 구성합니다."""
        nx = self._networkx()
        cluster_graphs = {name: nx.Graph() for name in self.PREDEFINED_CLUSTERS}
        concept_to_cluster = {
            concept: name
            for name, concepts in self.PREDEFINED_CLUSTERS.items()
            for concept in concepts
        }
        for record in records:
            if str(record.get("category") or "") == "미분류":
                continue
            concepts = self._record_concepts(record)
            by_cluster: dict[str, list[str]] = defaultdict(list)
            for concept in concepts:
                cluster_name = concept_to_cluster.get(concept)
                if cluster_name:
                    by_cluster[cluster_name].append(concept)
            for cluster_name, cluster_concepts in by_cluster.items():
                graph = cluster_graphs[cluster_name]
                for concept in cluster_concepts:
                    graph.add_node(concept)
                for source, target in combinations(cluster_concepts, 2):
                    weight = graph[source][target]["weight"] + 1 if graph.has_edge(source, target) else 1
                    graph.add_edge(source, target, weight=weight)

        clusters = []
        for name, graph in cluster_graphs.items():
            configured = self.PREDEFINED_CLUSTERS[name]
            existing = set(graph.nodes)
            subgraph = graph.subgraph(existing)
            cluster_concepts = sorted(
                configured,
                key=lambda node: subgraph.degree(node, weight="weight") if node in subgraph else 0,
                reverse=True,
            )
            importance = int(sum(dict(subgraph.degree(weight="weight")).values())) + len(existing)
            clusters.append(
                {
                    "id": name,
                    "concepts": cluster_concepts,
                    "importance": importance,
                }
            )
        clusters.sort(key=lambda item: item["importance"], reverse=True)
        return {
            "clusters": clusters,
            "node_count": sum(graph.number_of_nodes() for graph in cluster_graphs.values()),
            "edge_count": sum(graph.number_of_edges() for graph in cluster_graphs.values()),
        }

    def format_report(self, analysis: dict[str, Any]) -> str:
        """Topic Cluster 분석 결과를 문자열로 변환합니다."""
        clusters = analysis.get("clusters", [])
        if not clusters:
            return "Topic Cluster\n- 데이터 없음"
        lines = ["Topic Cluster"]
        for cluster in clusters[:15]:
            lines.append(f"- {', '.join(cluster['concepts'][:8])} / 중요도 {cluster['importance']}")
        return "\n".join(lines)

    def cluster_score_map(self, analysis: dict[str, Any]) -> dict[str, float]:
        """출제 가능성 계산용 클러스터 중요도 점수를 반환합니다."""
        scores = {}
        max_importance = max([cluster["importance"] for cluster in analysis.get("clusters", [])] or [1])
        for cluster in analysis.get("clusters", []):
            score = cluster["importance"] / max_importance
            for concept in cluster["concepts"]:
                scores[concept] = max(scores.get(concept, 0), score)
        return scores

    def _record_concepts(self, record: dict[str, Any]) -> list[str]:
        values = [
            str(record.get("primary") or record.get("subcategory") or ""),
            *self._as_list(record.get("secondary")),
            *self._as_list(record.get("concepts")),
        ]
        result = []
        seen = set()
        for value in values:
            item = str(value).strip()
            if item and item != "미분류" and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    def _as_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        return [item.strip() for item in str(value or "").split(",") if item.strip()]

    def _networkx(self):
        try:
            import networkx as nx
        except ImportError as exc:
            raise RuntimeError("networkx가 필요합니다. requirements.txt를 설치하세요.") from exc
        return nx
