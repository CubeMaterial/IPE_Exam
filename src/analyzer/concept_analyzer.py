"""개념 분석 기능을 제공합니다."""

from __future__ import annotations

from config.prompt import CONCEPT_ANALYSIS_PROMPT
from src.llm.ollama_client import OllamaClient
from src.rag.retriever import Retriever


class ConceptAnalyzer:
    """학습 개념을 시험 대비 관점으로 분석합니다."""

    def __init__(self, retriever: Retriever | None = None, llm: OllamaClient | None = None) -> None:
        """검색기와 LLM 의존성을 초기화합니다."""
        self.retriever = retriever or Retriever()
        self.llm = llm or OllamaClient()

    def analyze(self, concept: str) -> str:
        """개념명 또는 설명을 분석해 학습 포인트를 반환합니다."""
        # 등록된 문서가 있다면 관련 Chunk를 함께 제공해 자료 기반 분석을 유도합니다.
        chunks = self.retriever.retrieve(concept)
        context = "\n\n".join(chunk.text for chunk in chunks) or "참고 문서 없음"
        prompt = f"분석할 개념:\n{concept}\n\n참고 자료:\n{context}"
        return self.llm.generate(CONCEPT_ANALYSIS_PROMPT, prompt)
