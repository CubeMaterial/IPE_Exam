"""TXT 문서 로더를 제공합니다."""

from __future__ import annotations

from pathlib import Path

from src.models import Document
from src.utils.exceptions import DocumentLoadError
from src.utils.file_utils import write_processed_text


class TxtLoader:
    """TXT 파일에서 텍스트를 읽는 로더입니다."""

    def load(self, path: Path) -> Document:
        """TXT 파일을 읽어 Document로 반환합니다."""
        try:
            text = path.read_text(encoding="utf-8").strip()
        except UnicodeDecodeError:
            try:
                text = path.read_text(encoding="cp949").strip()
            except Exception as exc:
                raise DocumentLoadError(f"TXT 인코딩을 읽을 수 없습니다: {path}") from exc
        except Exception as exc:
            raise DocumentLoadError(f"TXT 파일 읽기에 실패했습니다: {path}") from exc

        write_processed_text(path, text)
        return Document(source_path=path, text=text, document_type="txt")
