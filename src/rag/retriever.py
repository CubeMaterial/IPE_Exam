"""RAG 검색기를 제공합니다."""

from __future__ import annotations

from config.config import CONFIG
from src.embedding.embedding import ChromaEmbeddingStore
from src.models import RetrievedChunk


class Retriever:
    """사용자 질문과 관련된 Chunk를 검색합니다."""

    def __init__(self, store: ChromaEmbeddingStore | None = None) -> None:
        """벡터 저장소 의존성을 초기화합니다."""
        self.store = store or ChromaEmbeddingStore()

    def retrieve(self, question: str, top_k: int = CONFIG.top_k) -> list[RetrievedChunk]:
        """질문과 유사한 Chunk 목록을 반환합니다."""
        result = self.store.query(question, top_k=top_k)
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
