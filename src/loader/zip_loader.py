"""ZIP 문서 로더를 제공합니다."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from config.config import CONFIG
from src.models import Document
from src.utils.exceptions import DocumentLoadError, UnsupportedFileError
from src.utils.file_utils import normalize_extension


class ZipLoader:
    """ZIP 파일을 해제하고 내부 문서를 자동 분류해 읽는 로더입니다."""

    def __init__(self, dispatcher: "DocumentDispatcher") -> None:
        """내부 파일 처리를 위한 문서 분배기를 초기화합니다."""
        self.dispatcher = dispatcher

    def load(self, path: Path) -> list[Document]:
        """ZIP 파일 내부의 지원 문서를 읽어 Document 목록으로 반환합니다."""
        try:
            extract_dir = CONFIG.temp_data_dir / path.stem
            extract_dir.mkdir(parents=True, exist_ok=True)
            documents: list[Document] = []
            with ZipFile(path) as archive:
                archive.extractall(extract_dir)
            for child in extract_dir.rglob("*"):
                if child.is_file() and normalize_extension(child) != ".zip":
                    try:
                        documents.extend(self.dispatcher.load(child))
                    except UnsupportedFileError:
                        continue
            return documents
        except Exception as exc:
            raise DocumentLoadError(f"ZIP 파일 처리에 실패했습니다: {path}") from exc


from src.loader.dispatcher import DocumentDispatcher  # noqa: E402  pylint: disable=wrong-import-position
