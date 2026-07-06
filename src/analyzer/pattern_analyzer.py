"""출제 패턴 분석 기능을 제공합니다."""

from __future__ import annotations

from config.prompt import QUESTION_ANALYSIS_PROMPT
from src.llm.ollama_client import OllamaClient


class PatternAnalyzer:
    """여러 문제에서 반복되는 출제 패턴을 분석합니다."""

    def __init__(self, llm: OllamaClient | None = None) -> None:
        """LLM 의존성을 초기화합니다."""
        self.llm = llm or OllamaClient()

    def analyze(self, questions: str) -> str:
        """문제 묶음에서 공통 출제 패턴과 변형 가능성을 분석합니다."""
        prompt = f"다음 문제들의 공통 출제 패턴을 분석하세요.\n\n{questions}"
        return self.llm.generate(QUESTION_ANALYSIS_PROMPT, prompt)
