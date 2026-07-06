"""문서 텍스트를 Chunk로 분리하는 기능을 제공합니다."""

from __future__ import annotations

from src.models import Document, DocumentChunk


class TextChunker:
    """길이와 Overlap 설정에 따라 문서를 Chunk로 나눕니다."""

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        """Chunk 크기와 Overlap을 초기화합니다."""
        if chunk_size <= 0:
            raise ValueError("chunk_size는 0보다 커야 합니다.")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap은 0 이상이며 chunk_size보다 작아야 합니다.")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, document: Document) -> list[DocumentChunk]:
        """Document 텍스트를 DocumentChunk 목록으로 분리합니다."""
        text = document.text.strip()
        if not text:
            return []

        chunks: list[DocumentChunk] = []
        start = 0
        chunk_number = 1
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk_id = f"{document.source_path.stem}_{chunk_number}"
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        source_path=document.source_path,
                        chunk_number=chunk_number,
                        text=chunk_text,
                        metadata=document.metadata | {"document_type": document.document_type},
                    )
                )
            if end == len(text):
                break
            start = end - self.chunk_overlap
            chunk_number += 1
        return chunks
