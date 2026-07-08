"""Ollama 임베딩과 ChromaDB 저장 기능을 제공합니다."""

from __future__ import annotations

import shutil
from typing import Any

from config.config import CONFIG
from src.llm.ollama_client import OllamaClient
from src.models import DocumentChunk
from src.utils.exceptions import VectorStoreError


class ChromaEmbeddingStore:
    """DocumentChunk를 임베딩하여 ChromaDB에 저장하고 검색합니다."""

    def __init__(self, ollama_client: OllamaClient | None = None) -> None:
        """Ollama 클라이언트와 Chroma 컬렉션을 초기화합니다."""
        self.ollama_client = ollama_client or OllamaClient()
        self._client = None
        self._collection = None

    def add_chunks(self, chunks: list[DocumentChunk]) -> int:
        """Chunk 목록을 임베딩하여 ChromaDB에 저장합니다."""
        if not chunks:
            return 0
        try:
            collection = self._get_collection()
            embeddings = [self.ollama_client.embed(chunk.text) for chunk in chunks]
            collection.upsert(
                ids=[chunk.chunk_id for chunk in chunks],
                documents=[chunk.text for chunk in chunks],
                embeddings=embeddings,
                metadatas=[self._metadata(chunk) for chunk in chunks],
            )
            return len(chunks)
        except Exception as exc:
            raise VectorStoreError("Chunk 저장 중 오류가 발생했습니다.") from exc

    def query(
        self,
        query_text: str,
        top_k: int = CONFIG.top_k,
        metadata_filter: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """질문 텍스트와 유사한 Chunk를 검색합니다."""
        try:
            collection = self._get_collection()
            if collection.count() == 0:
                return {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}
            query_embedding = self.ollama_client.embed(query_text)
            query_args: dict[str, Any] = {
                "query_embeddings": [query_embedding],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            }
            if metadata_filter:
                query_args["where"] = metadata_filter
            return collection.query(**query_args)
        except Exception as exc:
            raise VectorStoreError("Chunk 검색 중 오류가 발생했습니다.") from exc

    def reset(self) -> None:
        """ChromaDB 저장소를 초기화합니다."""
        self._client = None
        self._collection = None
        if CONFIG.chroma_dir.exists():
            shutil.rmtree(CONFIG.chroma_dir)
        CONFIG.chroma_dir.mkdir(parents=True, exist_ok=True)

    def delete_by_filter(self, metadata_filter: dict[str, Any]) -> int:
        """메타데이터 조건에 맞는 Chunk를 삭제하고 삭제 개수를 반환합니다."""
        try:
            collection = self._get_collection()
            if collection.count() == 0:
                return 0
            result = collection.get(where=metadata_filter)
            ids = result.get("ids", [])
            if not ids:
                return 0
            collection.delete(ids=ids)
            return len(ids)
        except Exception as exc:
            raise VectorStoreError("조건에 맞는 Chunk 삭제 중 오류가 발생했습니다.") from exc

    def _get_collection(self):
        """Chroma 컬렉션을 지연 생성합니다."""
        if self._collection is None:
            try:
                import chromadb
            except ImportError as exc:
                raise VectorStoreError("ChromaDB가 설치되어 있지 않습니다. requirements.txt를 설치하세요.") from exc
            self._client = chromadb.PersistentClient(path=str(CONFIG.chroma_dir))
            self._collection = self._client.get_or_create_collection(name=CONFIG.collection_name)
        return self._collection

    def _metadata(self, chunk: DocumentChunk) -> dict[str, Any]:
        """ChromaDB에 저장 가능한 메타데이터를 생성합니다."""
        metadata = {
            "source_path": str(chunk.source_path),
            "source_name": chunk.source_path.name,
            "chunk_number": chunk.chunk_number,
        }
        for key, value in chunk.metadata.items():
            if isinstance(value, str | int | float | bool):
                metadata[key] = value
        return metadata
