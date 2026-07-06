"""예상문제 생성 기능을 제공합니다."""

from __future__ import annotations

from config.prompt import EXPECTED_QUESTION_PROMPT
from src.llm.ollama_client import OllamaClient


class ExpectedQuestionGenerator:
    """기출 또는 개념을 기반으로 예상문제를 생성합니다."""

    def __init__(self, llm: OllamaClient | None = None) -> None:
        """LLM 의존성을 초기화합니다."""
        self.llm = llm or OllamaClient()

    def generate(self, source_text: str, question_type: str) -> str:
        """지정한 문제 유형으로 예상문제를 생성합니다."""
        prompt = f"문제 유형: {question_type}\n\n기준 자료:\n{source_text}"
        return self.llm.generate(EXPECTED_QUESTION_PROMPT, prompt)
