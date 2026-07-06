"""검색 결과를 기반으로 RAG 답변을 생성합니다."""

from __future__ import annotations

from config.prompt import GENERAL_QA_PROMPT, SUMMARY_PROMPT, FLASHCARD_PROMPT
from src.llm.ollama_client import OllamaClient
from src.models import RetrievedChunk
from src.rag.retriever import Retriever


class RAGGenerator:
    """검색된 Chunk를 근거로 학습 답변을 생성합니다."""

    def __init__(self, retriever: Retriever | None = None, llm: OllamaClient | None = None) -> None:
        """검색기와 LLM 의존성을 초기화합니다."""
        self.retriever = retriever or Retriever()
        self.llm = llm or OllamaClient()

    def answer(self, question: str) -> str:
        """질문에 대해 참고 문서와 Chunk 번호를 포함한 답변을 생성합니다."""
        chunks = self.retriever.retrieve(question)
        context = self._format_context(chunks)
        user_prompt = f"질문:\n{question}\n\n참고 문서 Chunk:\n{context}"
        answer = self.llm.generate(GENERAL_QA_PROMPT, user_prompt)
        return f"{answer}\n\n{self._format_references(chunks)}"

    def summarize(self, query: str, summary_type: str) -> str:
        """검색된 자료를 지정한 형식으로 요약합니다."""
        chunks = self.retriever.retrieve(query)
        context = self._format_context(chunks)
        user_prompt = f"요약 요청: {query}\n요약 형식: {summary_type}\n\n참고 자료:\n{context}"
        return self.llm.generate(SUMMARY_PROMPT, user_prompt)

    def make_flashcards(self, topic: str) -> str:
        """검색된 자료를 기반으로 암기 카드를 생성합니다."""
        chunks = self.retriever.retrieve(topic)
        context = self._format_context(chunks)
        user_prompt = f"암기 카드 주제: {topic}\n\n참고 자료:\n{context}"
        return self.llm.generate(FLASHCARD_PROMPT, user_prompt)

    def _format_context(self, chunks: list[RetrievedChunk]) -> str:
        """검색 Chunk를 LLM 입력용 문자열로 변환합니다."""
        if not chunks:
            return "검색된 참고 문서가 없습니다."
        formatted = []
        for chunk in chunks:
            language = chunk.metadata.get("language")
            source_type = chunk.metadata.get("source_type", "document")
            meta = f" / type {source_type}"
            if language:
                meta += f" / language {language}"
            formatted.append(
                f"[문서: {chunk.source_path} / Chunk {chunk.chunk_number} / score {chunk.score:.3f}{meta}]\n"
                f"{chunk.text}"
            )
        return "\n\n".join(formatted)

    def _format_references(self, chunks: list[RetrievedChunk]) -> str:
        """사용자 출력용 참고 문서 목록을 생성합니다."""
        if not chunks:
            return "참고 문서: 없음"
        lines = ["참고 문서:"]
        for chunk in chunks:
            language = chunk.metadata.get("language")
            source_type = chunk.metadata.get("source_type", "document")
            extra = f" / {source_type}"
            if language:
                extra += f" / {language}"
            lines.append(f"- {chunk.source_path} / Chunk {chunk.chunk_number}{extra} / 유사도 {chunk.score:.3f}")
        return "\n".join(lines)
