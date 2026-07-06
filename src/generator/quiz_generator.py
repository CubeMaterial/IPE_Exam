"""퀴즈 생성 기능을 제공합니다."""

from __future__ import annotations

from src.generator.expected_question_generator import ExpectedQuestionGenerator


class QuizGenerator:
    """간단한 퀴즈 생성을 담당합니다."""

    def __init__(self, expected_generator: ExpectedQuestionGenerator | None = None) -> None:
        """예상문제 생성기 의존성을 초기화합니다."""
        self.expected_generator = expected_generator or ExpectedQuestionGenerator()

    def generate_quiz(self, topic: str, question_type: str = "객관식") -> str:
        """주제와 문제 유형에 맞는 퀴즈를 생성합니다."""
        return self.expected_generator.generate(topic, question_type)
