"""예상문제 생성 기능을 제공합니다."""

from __future__ import annotations

from config.prompt import EXPECTED_QUESTION_PROMPT
from src.llm.ollama_client import OllamaClient
from src.rag.retriever import Retriever
from src.embedding.embedding import ChromaEmbeddingStore


class ExpectedQuestionGenerator:
    """기출 또는 개념을 기반으로 예상문제를 생성합니다."""

    def __init__(
        self,
        llm: OllamaClient | None = None,
        retriever: Retriever | None = None,
        store: ChromaEmbeddingStore | None = None,
    ) -> None:
        """LLM 의존성을 초기화합니다."""
        self.llm = llm or OllamaClient()
        self.retriever = retriever or Retriever()
        self.store = store or ChromaEmbeddingStore()

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

    def generate_from_past_exams(
        self,
        topic: str,
        question_type: str,
        count: int,
        mode: str = "과년도 기출 기반",
        year: int | None = None,
        category: str = "",
        type_filter: str = "",
    ) -> str:
        """과년도 기출 메타데이터를 검색해 예상문제를 생성합니다."""
        metadata_filter = self._build_filter(mode, year, category, type_filter)
        result = self.store.query(topic, top_k=8, metadata_filter=metadata_filter)
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        context_lines = []
        for index, document in enumerate(documents):
            metadata = metadatas[index] if index < len(metadatas) else {}
            context_lines.append(
                f"[{metadata.get('year')}년 {metadata.get('round')}회 / "
                f"{metadata.get('category')} / {metadata.get('sub_category')} / "
                f"{metadata.get('question_type')}]\n{document}"
            )
        context = "\n\n".join(context_lines) or "검색된 과년도 기출 없음"
        prompt = (
            f"생성 방식: {mode}\n"
            f"문제 유형: {question_type}\n"
            f"문제 수: {count}개\n"
            f"요청 주제: {topic}\n\n"
            f"과년도 기출 참고:\n{context}"
        )
        return self.llm.generate(EXPECTED_QUESTION_PROMPT, prompt)

    def _build_filter(self, mode: str, year: int | None, category: str, type_filter: str) -> dict:
        """생성 옵션에 맞는 ChromaDB 메타데이터 필터를 생성합니다."""
        filters: list[dict] = [{"source_type": "past_exam"}]
        if mode == "최근 3개년 기반":
            recent_years = self._recent_years()
            if recent_years:
                filters.append({"year": {"$gte": min(recent_years)}})
        if mode == "특정 연도 기반" and year:
            filters.append({"year": int(year)})
        if mode == "특정 과목 기반" and category:
            filters.append({"category": category})
        if mode == "특정 유형 기반" and type_filter:
            filters.append({"question_type": type_filter})
        if len(filters) == 1:
            return filters[0]
        return {"$and": filters}

    def _recent_years(self) -> list[int]:
        """기출 JSON 인덱스에서 최근 3개년을 찾습니다."""
        try:
            from src.analyzer.past_exam_indexer import PastExamIndexer

            records = PastExamIndexer().load_index_records()
            years = sorted({int(record["year"]) for record in records if record.get("year")}, reverse=True)
            return years[:3]
        except Exception:
            return []
