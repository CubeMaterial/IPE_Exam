"""문서 텍스트 정리 기능을 제공합니다."""

from __future__ import annotations

import re


class TextCleaner:
    """문서에서 추출한 텍스트를 RAG에 적합하게 정리합니다."""

    def clean(self, text: str) -> str:
        """불필요한 공백과 제어문자를 정리합니다."""
        # OCR/PDF에서 섞여 들어오는 제어문자와 과도한 줄바꿈을 정규화합니다.
        normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()
