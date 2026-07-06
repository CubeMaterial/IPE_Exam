"""과년도 기출 분석 기능을 검증합니다."""

from __future__ import annotations

from unittest import TestCase

from src.analyzer.frequency_analyzer import FrequencyAnalyzer
from src.analyzer.past_exam_parser import PastExamParser


class PastExamParserTest(TestCase):
    """기출문제 파서 테스트입니다."""

    def test_parse_numbered_questions_with_answer(self) -> None:
        """문제 번호와 정답 영역을 분리합니다."""
        text = """
1. C 포인터 출력 결과는?
정답: 3

[문제 2] SQL JOIN 설명으로 옳은 것은?
해설: INNER JOIN은 교집합이다.
"""

        questions = PastExamParser().parse_questions(text)

        self.assertEqual(len(questions), 2)
        self.assertEqual(questions[0].question_number, 1)
        self.assertIn("C 포인터", questions[0].body)
        self.assertEqual(questions[0].answer, "3")
        self.assertEqual(questions[1].question_number, 2)
        self.assertIn("INNER JOIN", questions[1].explanation)
        self.assertTrue(PastExamParser().has_question_markers(text))


class FrequencyAnalyzerTest(TestCase):
    """기출 빈도 분석 테스트입니다."""

    def test_analyze_counts_category_and_language(self) -> None:
        """세부 유형과 언어별 빈도를 계산합니다."""
        records = [
            {"year": 2024, "round": 1, "category": "프로그래밍 언어 활용", "sub_category": "C 포인터", "question_type": "코드 출력", "language": "C"},
            {"year": 2025, "round": 2, "category": "프로그래밍 언어 활용", "sub_category": "C 포인터", "question_type": "코드 출력", "language": "C"},
            {"year": 2025, "round": 3, "category": "SQL 응용", "sub_category": "SQL JOIN", "question_type": "SQL 결과", "language": "SQL"},
        ]

        analysis = FrequencyAnalyzer().analyze(records)

        self.assertEqual(analysis["sub_category"]["C 포인터"], 2)
        self.assertEqual(analysis["language"]["C"], 2)
        self.assertEqual(analysis["question_type"]["코드 출력"], 2)
