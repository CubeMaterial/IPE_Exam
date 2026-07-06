"""전처리 모듈 기본 동작을 검증합니다."""

from __future__ import annotations

from pathlib import Path
from unittest import TestCase

from src.models import Document
from src.preprocess.chunker import TextChunker
from src.preprocess.cleaner import TextCleaner


class TextCleanerTest(TestCase):
    """텍스트 정리 기능 테스트입니다."""

    def test_clean_removes_extra_spaces(self) -> None:
        """과도한 공백과 줄바꿈이 정리되는지 확인합니다."""
        cleaner = TextCleaner()
        self.assertEqual(cleaner.clean("A   B\n\n\nC"), "A B\n\nC")


class TextChunkerTest(TestCase):
    """Chunk 분리 기능 테스트입니다."""

    def test_split_with_overlap(self) -> None:
        """Overlap을 유지하며 Chunk가 분리되는지 확인합니다."""
        document = Document(
            source_path=Path("sample.txt"),
            text="abcdefghij",
            document_type="txt",
        )
        chunker = TextChunker(chunk_size=4, chunk_overlap=1)
        chunks = chunker.split(document)

        self.assertEqual([chunk.text for chunk in chunks], ["abcd", "defg", "ghij"])
        self.assertEqual([chunk.chunk_number for chunk in chunks], [1, 2, 3])
