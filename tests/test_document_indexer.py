"""문서 등록 파일 수집 기능을 검증합니다."""

from __future__ import annotations

from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import TestCase

from src.rag.document_indexer import DocumentIndexer


class DocumentIndexerCollectTest(TestCase):
    """문서 등록 대상 파일 수집 테스트입니다."""

    def test_collect_supported_files_reads_pdf_txt_and_markdown_in_nested_folders(self) -> None:
        """지정 폴더의 하위 폴더까지 PDF, TXT, Markdown 문서를 재귀적으로 찾습니다."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "chapter" / "sql"
            nested.mkdir(parents=True)
            pdf_path = nested / "기출.pdf"
            txt_path = root / "정리.txt"
            md_path = nested / "기출.md"
            ignored_path = nested / "메모.tmp"
            pdf_path.write_text("pdf placeholder", encoding="utf-8")
            txt_path.write_text("txt placeholder", encoding="utf-8")
            md_path.write_text("markdown placeholder", encoding="utf-8")
            ignored_path.write_text("ignore", encoding="utf-8")

            files = DocumentIndexer().collect_supported_files([root])

            self.assertCountEqual(files, [txt_path.resolve(), md_path.resolve(), pdf_path.resolve()])

    def test_collect_supported_files_removes_duplicates(self) -> None:
        """같은 파일이 여러 경로로 들어와도 중복 등록하지 않습니다."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pdf_path = root / "sample.pdf"
            pdf_path.write_text("pdf placeholder", encoding="utf-8")

            files = DocumentIndexer().collect_supported_files([root, pdf_path])

            self.assertEqual(files, [pdf_path.resolve()])
