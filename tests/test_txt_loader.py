"""TXT 로더 동작을 검증합니다."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from src.loader.dispatcher import DocumentDispatcher
from src.loader.txt_loader import TxtLoader


class TxtLoaderTest(TestCase):
    """TXT 파일 인코딩 처리 테스트입니다."""

    def test_load_utf8_txt(self) -> None:
        """UTF-8 TXT 파일을 기본 인코딩으로 읽습니다."""
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.txt"
            path.write_text("운영체제 핵심", encoding="utf-8")

            self.assertEqual(TxtLoader().load(path), "운영체제 핵심")

    def test_load_cp949_txt(self) -> None:
        """UTF-8 실패 시 cp949 인코딩으로 재시도합니다."""
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.txt"
            path.write_bytes("데이터베이스 정규화".encode("cp949"))

            self.assertEqual(TxtLoader().load(path), "데이터베이스 정규화")

    def test_dispatcher_wraps_txt_as_document(self) -> None:
        """문서 등록 분기에서 TXT가 Document로 변환되는지 확인합니다."""
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.txt"
            path.write_text("SQL JOIN", encoding="utf-8")

            documents = DocumentDispatcher().load(path)

            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0].document_type, "txt")
            self.assertEqual(documents[0].text, "SQL JOIN")
