"""RAG 검색기를 제공합니다."""

from __future__ import annotations

from config.config import CONFIG
from src.embedding.embedding import ChromaEmbeddingStore
from src.models import RetrievedChunk
from src.utils.code_utils import detect_language_in_query, is_code_related_query


class Retriever:
    """사용자 질문과 관련된 Chunk를 검색합니다."""

    def __init__(self, store: ChromaEmbeddingStore | None = None) -> None:
        """벡터 저장소 의존성을 초기화합니다."""
        self.store = store or ChromaEmbeddingStore()

    def retrieve(self, question: str, top_k: int = CONFIG.top_k) -> list[RetrievedChunk]:
        """질문과 유사한 Chunk 목록을 반환합니다."""
        preferred_filter = self._build_preferred_filter(question)
        if not preferred_filter:
            return self._query_chunks(question, top_k)

        preferred = self._query_chunks(question, top_k, preferred_filter)
        if len(preferred) >= top_k:
            return preferred[:top_k]

        fallback = self._query_chunks(question, top_k)
        merged = self._merge_unique(preferred, fallback)
        return merged[:top_k]

    def _query_chunks(
        self,
        question: str,
        top_k: int,
        metadata_filter: dict | None = None,
    ) -> list[RetrievedChunk]:
        """메타데이터 필터를 적용해 Chunk 목록을 검색합니다."""
        result = self.store.query(question, top_k=top_k, metadata_filter=metadata_filter)
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        ids = result.get("ids", [[]])[0]

        chunks: list[RetrievedChunk] = []
        for index, text in enumerate(documents):
            metadata = metadatas[index] if index < len(metadatas) else {}
            distance = float(distances[index]) if index < len(distances) else 0.0
            chunk_id = str(ids[index]) if index < len(ids) else f"chunk_{index + 1}"
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    source_path=str(metadata.get("source_path", "")),
                    chunk_number=int(metadata.get("chunk_number", index + 1)),
                    text=str(text),
                    score=1.0 / (1.0 + distance),
                    metadata=metadata,
                )
            )
        return chunks

    def _build_preferred_filter(self, question: str) -> dict | None:
        """질문에 맞는 코드 우선 검색 필터를 생성합니다."""
        language = detect_language_in_query(question)
        if language:
            return {"$and": [{"source_type": "code"}, {"language": language}]}
        if is_code_related_query(question):
            return {"source_type": "code"}
        return None

    def _merge_unique(self, primary: list[RetrievedChunk], secondary: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """우선 검색 결과와 일반 검색 결과를 중복 없이 합칩니다."""
        merged: list[RetrievedChunk] = []
        seen: set[str] = set()
        for chunk in primary + secondary:
            if chunk.chunk_id in seen:
                continue
            seen.add(chunk.chunk_id)
            merged.append(chunk)
        return merged
