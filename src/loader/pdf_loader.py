"""PDF 문서 로더를 제공합니다."""

from __future__ import annotations

from pathlib import Path

from config.config import CONFIG
from src.models import Document
from src.ocr.easyocr_engine import EasyOCREngine
from src.utils.exceptions import DocumentLoadError
from src.utils.file_utils import write_processed_text


class PdfLoader:
    """PyMuPDF로 PDF 텍스트를 추출하고 필요 시 OCR을 수행하는 로더입니다."""

    def __init__(self, ocr_engine: EasyOCREngine | None = None) -> None:
        """OCR 엔진 의존성을 초기화합니다."""
        self.ocr_engine = ocr_engine or EasyOCREngine()

    def load(self, path: Path) -> Document:
        """PDF 파일을 읽어 Document로 반환합니다."""
        try:
            import fitz
        except ImportError as exc:
            raise DocumentLoadError("PyMuPDF가 설치되어 있지 않습니다. requirements.txt를 설치하세요.") from exc

        try:
            with fitz.open(path) as pdf:
                page_texts = [page.get_text("text").strip() for page in pdf]
                text = "\n\n".join(item for item in page_texts if item).strip()
                if not text:
                    text = self._extract_scanned_pdf_text(pdf, path, fitz)

            write_processed_text(path, text)
            return Document(source_path=path, text=text, document_type="pdf")
        except Exception as exc:
            raise DocumentLoadError(f"PDF 파일 처리에 실패했습니다: {path}") from exc

    def _extract_scanned_pdf_text(self, pdf, source_path: Path, fitz_module) -> str:
        """텍스트가 없는 스캔 PDF를 이미지로 변환한 뒤 OCR을 수행합니다."""
        # 페이지별 PNG를 temp 폴더에 만들고 OCR 결과를 하나의 문서 텍스트로 합칩니다.
        extracted: list[str] = []
        for index, page in enumerate(pdf, start=1):
            pixmap = page.get_pixmap(matrix=fitz_module.Matrix(2, 2))
            image_path = CONFIG.temp_data_dir / f"{source_path.stem}_page_{index}.png"
            pixmap.save(image_path)
            page_text = self.ocr_engine.extract_text(image_path, save_processed=False)
            if page_text:
                extracted.append(f"[page {index}]\n{page_text}")
        return "\n\n".join(extracted).strip()
