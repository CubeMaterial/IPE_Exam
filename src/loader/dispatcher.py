"""파일 형식에 맞는 문서 로더로 분배하는 모듈입니다."""

from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import unquote

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
        if extension in {".txt", ".md"}:
            text = self.txt_loader.load(path)
            document_type = "markdown" if extension == ".md" else "txt"
            if extension == ".md":
                text = self._append_markdown_image_ocr(path, text)
            return [Document(source_path=path, text=text, document_type=document_type)]
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

    def _append_markdown_image_ocr(self, path: Path, text: str) -> str:
        """Markdown 안의 로컬 이미지 링크를 OCR해 본문 뒤에 붙입니다."""
        image_paths = self._markdown_image_paths(path, text)
        if not image_paths:
            return text

        parts = [text]
        missing = []
        for image_path in image_paths:
            if not image_path.exists():
                missing.append(str(image_path))
                continue
            try:
                image_document = self.image_loader.load(image_path)
            except Exception as exc:
                parts.append(f"\n\n[이미지 OCR 실패: {image_path.name} / {exc}]")
                continue
            parts.append(f"\n\n[이미지 OCR: {image_path.name}]\n{image_document.text}")
        if missing:
            parts.append("\n\n[Markdown 참조 이미지 없음]\n" + "\n".join(f"- {item}" for item in missing))
        return "\n".join(parts)

    def _markdown_image_paths(self, path: Path, text: str) -> list[Path]:
        """Markdown 이미지 링크에서 로컬 파일 경로를 추출합니다."""
        candidates = []
        patterns = [
            r"!\[.*?\]\(([^)]+)\)",
            r"!\[[^\]]*\]\(([^)]+)\)",
            r"!\[\[[^\]]*\]\(([^)]+)\)",
            r"!\[\[([^]|]+)(?:\|[^\]]+)?\]\]",
            r"<img[^>]+src=[\"']([^\"']+)[\"']",
        ]
        for pattern in patterns:
            candidates.extend(re.findall(pattern, text, flags=re.IGNORECASE))

        resolved: list[Path] = []
        seen: set[Path] = set()
        for candidate in candidates:
            raw = unquote(candidate.strip()).split("#", 1)[0].split("?", 1)[0]
            if raw.startswith(("http://", "https://", "data:")):
                continue
            image_path = Path(raw)
            if not image_path.is_absolute():
                image_path = path.parent / image_path
            image_path = image_path.expanduser()
            if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                continue
            normalized = image_path
            if normalized not in seen:
                seen.add(normalized)
                resolved.append(normalized)
        return resolved
