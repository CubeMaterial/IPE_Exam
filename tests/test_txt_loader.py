"""텍스트 로더 동작을 검증합니다."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from src.loader.dispatcher import DocumentDispatcher
from src.loader.txt_loader import TxtLoader


class TxtLoaderTest(TestCase):
    """TXT/Markdown 파일 인코딩 처리 테스트입니다."""

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

    def test_load_utf8_markdown(self) -> None:
        """UTF-8 Markdown 파일을 텍스트로 읽습니다."""
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "past_exam.md"
            path.write_text("# 2025년 1회\n\n1. SQL 문제", encoding="utf-8")

            self.assertEqual(TxtLoader().load(path), "# 2025년 1회\n\n1. SQL 문제")

    def test_dispatcher_wraps_txt_as_document(self) -> None:
        """문서 등록 분기에서 TXT가 Document로 변환되는지 확인합니다."""
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.txt"
            path.write_text("SQL JOIN", encoding="utf-8")

            documents = DocumentDispatcher().load(path)

            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0].document_type, "txt")
            self.assertEqual(documents[0].text, "SQL JOIN")

    def test_dispatcher_wraps_markdown_as_document(self) -> None:
        """문서 등록 분기에서 Markdown이 Document로 변환되는지 확인합니다."""
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "past_exam.md"
            path.write_text("1. 디자인 패턴 문제", encoding="utf-8")

            documents = DocumentDispatcher().load(path)

            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0].document_type, "markdown")
            self.assertEqual(documents[0].text, "1. 디자인 패턴 문제")

    def test_dispatcher_finds_markdown_image_links(self) -> None:
        """Markdown 이미지 링크의 상대 경로를 추출합니다."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            assets = root / "assets"
            assets.mkdir()
            image_path = assets / "exam.png"
            image_path.write_bytes(b"fake image")
            path = root / "past_exam.md"
            path.write_text("![[문제 이미지](assets/exam.png)]", encoding="utf-8")

            image_paths = DocumentDispatcher()._markdown_image_paths(path, path.read_text(encoding="utf-8"))

            self.assertEqual(image_paths, [image_path])

    def test_dispatcher_finds_markdown_image_links_with_nested_brackets(self) -> None:
        """대괄호가 포함된 alt 텍스트의 이미지 링크도 추출합니다."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            assets = root / "assets"
            assets.mkdir()
            image_path = assets / "exam.png"
            image_path.write_bytes(b"fake image")
            path = root / "past_exam.md"
            text = "![[2025년 1회] 정보처리기사 실기 복원 문제](assets/exam.png)"
            path.write_text(text, encoding="utf-8")

            image_paths = DocumentDispatcher()._markdown_image_paths(path, text)

            self.assertEqual(image_paths, [image_path])
