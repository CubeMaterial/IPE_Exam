"""예상문제 생성 기능을 제공합니다."""

from __future__ import annotations

from config.prompt import EXPECTED_QUESTION_PROMPT
from src.llm.ollama_client import OllamaClient
from src.rag.retriever import Retriever


class ExpectedQuestionGenerator:
    """기출 또는 개념을 기반으로 예상문제를 생성합니다."""

    def __init__(self, llm: OllamaClient | None = None, retriever: Retriever | None = None) -> None:
        """LLM 의존성을 초기화합니다."""
        self.llm = llm or OllamaClient()
        self.retriever = retriever or Retriever()

    def generate(self, source_text: str, question_type: str) -> str:
        """지정한 문제 유형으로 예상문제를 생성합니다."""
        chunks = self.retriever.retrieve(source_text)
        context = "\n\n".join(
            f"[{chunk.metadata.get('source_type', 'document')} / {chunk.metadata.get('language', '')} / "
            f"{chunk.source_path} / Chunk {chunk.chunk_number}]\n{chunk.text}"
            for chunk in chunks
        ) or "검색된 등록 자료 없음"
        prompt = f"문제 유형: {question_type}\n\n요청:\n{source_text}\n\n등록 자료 참고:\n{context}"
        return self.llm.generate(EXPECTED_QUESTION_PROMPT, prompt)
