"""이미지 문서 로더를 제공합니다."""

from __future__ import annotations

from pathlib import Path

from src.models import Document
from src.ocr.easyocr_engine import EasyOCREngine
from src.utils.exceptions import DocumentLoadError


class ImageLoader:
    """이미지 파일에서 OCR 텍스트를 추출하는 로더입니다."""

    def __init__(self, ocr_engine: EasyOCREngine | None = None) -> None:
        """OCR 엔진 의존성을 초기화합니다."""
        self.ocr_engine = ocr_engine or EasyOCREngine()

    def load(self, path: Path) -> Document:
        """이미지 파일을 읽어 OCR 결과 Document로 반환합니다."""
        try:
            text = self.ocr_engine.extract_text(path)
            return Document(source_path=path, text=text, document_type="image")
        except Exception as exc:
            raise DocumentLoadError(f"이미지 파일 처리에 실패했습니다: {path}") from exc
