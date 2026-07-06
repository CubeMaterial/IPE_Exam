"""기출문제 분석 기능을 제공합니다."""

from __future__ import annotations

from config.prompt import QUESTION_ANALYSIS_PROMPT
from src.llm.ollama_client import OllamaClient


class QuestionAnalyzer:
    """기출문제의 유형과 출제 의도를 분석합니다."""

    def __init__(self, llm: OllamaClient | None = None) -> None:
        """LLM 의존성을 초기화합니다."""
        self.llm = llm or OllamaClient()

    def analyze(self, question_text: str) -> str:
        """기출문제 텍스트를 분석합니다."""
        prompt = f"다음 기출문제 또는 소스코드를 분석하세요.\n\n{question_text}"
        return self.llm.generate(QUESTION_ANALYSIS_PROMPT, prompt)
