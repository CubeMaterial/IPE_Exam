"""소스코드 전용 Chunk 분리 기능을 제공합니다."""

from __future__ import annotations

import hashlib
import re

from src.models import Document, DocumentChunk


class CodeChunker:
    """함수, 클래스, 메서드, 주석, 빈 줄 경계를 우선해 코드를 Chunk로 나눕니다."""

    _BOUNDARY_PATTERN = re.compile(
        r"^\s*(class|interface|enum|struct|def|func|function|fn|public|private|protected|static|"
        r"void|int|float|double|char|bool|String|fun|package|import|#include)\b"
    )
    _COMMENT_PATTERN = re.compile(r"^\s*(//|#|/\*|\*|<!--|--)")

    def __init__(self, chunk_size: int) -> None:
        """코드 Chunk 최대 크기를 초기화합니다."""
        if chunk_size <= 0:
            raise ValueError("code_chunk_size는 0보다 커야 합니다.")
        self.chunk_size = chunk_size

    def split(self, document: Document) -> list[DocumentChunk]:
        """코드 Document를 의미 있는 단위의 DocumentChunk 목록으로 분리합니다."""
        text = document.text.rstrip()
        if not text:
            return []

        sections = self._split_sections(text)
        chunks: list[DocumentChunk] = []
        chunk_number = 1
        for section in sections:
            for piece in self._split_large_section(section):
                chunk_text = piece.strip()
                if not chunk_text:
                    continue
                chunks.append(
                    DocumentChunk(
                        chunk_id=self._chunk_id(document, chunk_number),
                        source_path=document.source_path,
                        chunk_number=chunk_number,
                        text=chunk_text,
                        metadata=document.metadata
                        | {
                            "document_type": document.document_type,
                            "chunk_strategy": "code",
                        },
                    )
                )
                chunk_number += 1
        return chunks

    def _split_sections(self, text: str) -> list[str]:
        """코드를 우선순위 경계에 따라 섹션으로 나눕니다."""
        sections: list[str] = []
        current: list[str] = []

        for line in text.splitlines():
            stripped = line.strip()
            is_boundary = self._is_boundary(line)
            should_flush = bool(current) and (
                is_boundary
                or (not stripped and sum(len(item) for item in current) >= self.chunk_size // 2)
                or (self._COMMENT_PATTERN.match(line) is not None and sum(len(item) for item in current) >= self.chunk_size)
            )
            if should_flush:
                sections.append("\n".join(current).strip())
                current = []
            current.append(line)

        if current:
            sections.append("\n".join(current).strip())
        return [section for section in sections if section]

    def _split_large_section(self, section: str) -> list[str]:
        """너무 큰 코드 섹션을 설정된 Chunk 크기에 맞게 추가 분리합니다."""
        if len(section) <= self.chunk_size:
            return [section]

        pieces: list[str] = []
        current: list[str] = []
        current_size = 0
        for line in section.splitlines():
            line_size = len(line) + 1
            if current and current_size + line_size > self.chunk_size:
                pieces.append("\n".join(current))
                current = []
                current_size = 0
            current.append(line)
            current_size += line_size
        if current:
            pieces.append("\n".join(current))
        return pieces

    def _is_boundary(self, line: str) -> bool:
        """라인이 함수, 클래스, 메서드, 주석 경계인지 확인합니다."""
        return self._BOUNDARY_PATTERN.match(line) is not None or self._COMMENT_PATTERN.match(line) is not None

    def _chunk_id(self, document: Document, chunk_number: int) -> str:
        """파일 경로 기반으로 충돌 가능성이 낮은 Chunk ID를 생성합니다."""
        digest = hashlib.sha1(str(document.source_path.resolve()).encode("utf-8")).hexdigest()[:10]
        return f"{document.source_path.stem}_{digest}_{chunk_number}"
