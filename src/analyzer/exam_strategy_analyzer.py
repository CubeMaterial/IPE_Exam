"""과년도 기출 기반 다음 시험 대비 전략을 생성합니다."""

from __future__ import annotations

from typing import Any

from src.analyzer.frequency_analyzer import FrequencyAnalyzer
from src.llm.ollama_client import OllamaClient


STRATEGY_PROMPT = """
당신은 정보처리기사 실기 학습 전략 코치입니다.
반드시 "과거 기출 기반의 가능성 분석"이라고 표현하세요.
정확한 예언처럼 말하지 마세요.
아래 12개 항목을 한국어로 작성하세요.
1. 전체 출제 경향 요약
2. 최근 3개년 핵심 변화
3. 가장 자주 나온 과목 TOP 10
4. 가장 자주 나온 세부 유형 TOP 20
5. 다음 시험에서 우선 봐야 할 과목
6. 다음 시험에서 우선 봐야 할 세부 개념
7. 코드 문제 대비 전략
8. SQL 문제 대비 전략
9. 암기 문제 대비 전략
10. 버려도 되는 저빈도 영역
11. 남은 기간별 공부 우선순위
12. 예상 출제 가능성이 높은 문제 유형
""".strip()


class ExamStrategyAnalyzer:
    """기출 빈도 분석 결과를 바탕으로 다음 시험 대비 전략을 생성합니다."""

    def __init__(self, llm: OllamaClient | None = None, frequency_analyzer: FrequencyAnalyzer | None = None) -> None:
        """LLM과 빈도 분석기 의존성을 초기화합니다."""
        self.llm = llm or OllamaClient()
        self.frequency_analyzer = frequency_analyzer or FrequencyAnalyzer()

    def generate_strategy(self, records: list[dict[str, Any]]) -> str:
        """기출 인덱스 레코드를 바탕으로 전략 보고서를 생성합니다."""
        analysis = self.frequency_analyzer.analyze(records)
        report = self.frequency_analyzer.format_report(analysis)
        try:
            return self.llm.generate(STRATEGY_PROMPT, f"기출 빈도 분석 데이터:\n{report}")
        except Exception:
            return self._fallback_strategy(analysis)

    def _fallback_strategy(self, analysis: dict[str, Any]) -> str:
        """LLM 호출 실패 시 빈도 기반 기본 전략을 생성합니다."""
        top_subjects = analysis["question_type"].most_common(10)
        top_details = analysis["sub_category"].most_common(20)
        return (
            "과거 기출 기반의 가능성 분석입니다.\n\n"
            "1. 전체 출제 경향 요약\n"
            "- 등록된 기출 인덱스를 기준으로 반복 출제 영역을 우선 정리해야 합니다.\n\n"
            "2. 최근 3개년 핵심 변화\n"
            f"{self.frequency_analyzer._format_counter(analysis['recent_increased'])}\n\n"
            "3. 가장 자주 나온 과목 TOP 10\n"
            f"{self.frequency_analyzer._format_counter(analysis['question_type'])}\n\n"
            "4. 가장 자주 나온 세부 유형 TOP 20\n"
            f"{self.frequency_analyzer._format_counter(analysis['sub_category'])}\n\n"
            "5. 다음 시험에서 우선 봐야 할 과목\n"
            f"- {', '.join(item for item, _ in top_subjects[:5]) or '데이터 추가 필요'}\n\n"
            "6. 다음 시험에서 우선 봐야 할 세부 개념\n"
            f"- {', '.join(item for item, _ in top_details[:8]) or '데이터 추가 필요'}\n\n"
            "7. 코드 문제 대비 전략\n- C 포인터, Java 상속, Python 자료구조형 출력 흐름을 반복하세요.\n\n"
            "8. SQL 문제 대비 전략\n- JOIN, GROUP BY, HAVING, 서브쿼리 결과 예측을 우선하세요.\n\n"
            "9. 암기 문제 대비 전략\n- 보안, 네트워크, 테스트 관리 용어를 짧은 카드로 반복하세요.\n\n"
            "10. 버려도 되는 저빈도 영역\n- 빈도가 낮은 영역은 핵심 용어 수준으로 압축하세요.\n\n"
            "11. 남은 기간별 공부 우선순위\n- 1단계 빈출 코드/SQL, 2단계 보안/네트워크, 3단계 저빈도 암기 영역 순서로 보세요.\n\n"
            "12. 예상 출제 가능성이 높은 문제 유형\n"
            f"{self.frequency_analyzer._format_counter(analysis['repeated_types'])}"
        )
