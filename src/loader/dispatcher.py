"""파일 형식에 맞는 문서 로더로 분배하는 모듈입니다."""

from __future__ import annotations

from pathlib import Path

from src.loader.code_loader import CodeLoader
from src.loader.image_loader import ImageLoader
from src.loader.pdf_loader import PdfLoader
from src.loader.txt_loader import TxtLoader
from src.models import Document
from src.utils.code_utils import is_code_file
from src.utils.exceptions import UnsupportedFileError
from src.utils.file_utils import normalize_extension, validate_supported_file


class DocumentDispatcher:
    """확장자에 따라 적절한 로더를 선택하는 분배기입니다."""

    def __init__(self) -> None:
        """문서 로더들을 초기화합니다."""
        self.pdf_loader = PdfLoader()
        self.txt_loader = TxtLoader()
        self.image_loader = ImageLoader()
        self.code_loader = CodeLoader()

    def load(self, path: Path) -> list[Document]:
        """파일을 자동 분류하여 Document 목록으로 반환합니다."""
        validate_supported_file(path)
        extension = normalize_extension(path)

        if extension == ".pdf":
            return [self.pdf_loader.load(path)]
        if extension == ".txt":
            text = self.txt_loader.load(path)
            return [Document(source_path=path, text=text, document_type="txt")]
        if extension in {".png", ".jpg", ".jpeg"}:
            return [self.image_loader.load(path)]
        if extension == ".zip":
            from src.loader.zip_loader import ZipLoader

            return ZipLoader(self).load(path)
        if is_code_file(path):
            text = self.code_loader.load(path)
            return [
                Document(
                    source_path=path,
                    text=text,
                    document_type="code",
                    metadata=self.code_loader.metadata(path),
                )
            ]

        raise UnsupportedFileError(f"지원하지 않는 파일 형식입니다: {path}")
