"""EasyOCR 기반 OCR 엔진을 제공합니다."""

from __future__ import annotations

from pathlib import Path

from config.config import CONFIG
from src.utils.exceptions import OCRError
from src.utils.file_utils import write_processed_text


class EasyOCREngine:
    """이미지 파일에서 텍스트를 추출하는 OCR 엔진입니다."""

    def __init__(self, languages: tuple[str, ...] = CONFIG.ocr_languages) -> None:
        """OCR 언어 설정을 초기화합니다."""
        self.languages = list(languages)
        self._reader = None

    def _get_reader(self):
        """EasyOCR Reader를 지연 생성합니다."""
        # EasyOCR은 무거운 의존성이므로 OCR이 필요할 때만 import합니다.
        if self._reader is None:
            try:
                import easyocr
            except ImportError as exc:
                raise OCRError("EasyOCR이 설치되어 있지 않습니다. requirements.txt를 설치하세요.") from exc
            self._reader = easyocr.Reader(self.languages, gpu=False)
        return self._reader

    def extract_text(self, image_path: Path, save_processed: bool = True) -> str:
        """이미지 파일에서 OCR 텍스트를 추출합니다."""
        if not CONFIG.ocr_enabled:
            return ""
        try:
            reader = self._get_reader()
            results = reader.readtext(str(image_path), detail=0, paragraph=True)
            text = "\n".join(str(item) for item in results).strip()
            if save_processed and text:
                write_processed_text(image_path, text, suffix=".ocr.txt")
            return text
        except OCRError:
            raise
        except Exception as exc:
            raise OCRError(f"OCR 처리 중 오류가 발생했습니다: {image_path}") from exc
