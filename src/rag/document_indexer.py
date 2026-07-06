"""문서 등록 파이프라인을 제공합니다."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from config.config import CONFIG
from src.embedding.embedding import ChromaEmbeddingStore
from src.loader.dispatcher import DocumentDispatcher
from src.preprocess.chunker import TextChunker
from src.preprocess.cleaner import TextCleaner
from src.utils.file_utils import copy_to_raw


ProgressCallback = Callable[[int], None]
LogCallback = Callable[[str], None]


@dataclass
class IndexReport:
    """문서 등록 결과를 GUI와 CLI에서 함께 사용할 수 있게 표현합니다."""

    processed_files: int = 0
    created_chunks: int = 0
    stored_location: Path = CONFIG.chroma_dir
    failed_files: list[str] = field(default_factory=list)

    def to_message(self) -> str:
        """등록 결과를 사용자에게 보여줄 문자열로 변환합니다."""
        failures = "\n".join(f"- {item}" for item in self.failed_files) or "없음"
        return (
            f"처리된 파일 수: {self.processed_files}\n"
            f"생성된 Chunk 수: {self.created_chunks}\n"
            f"저장 위치: {self.stored_location}\n"
            f"실패 파일 목록:\n{failures}"
        )


class DocumentIndexer:
    """문서 읽기부터 ChromaDB 저장까지 수행하는 등록 파이프라인입니다."""

    def __init__(
        self,
        dispatcher: DocumentDispatcher | None = None,
        cleaner: TextCleaner | None = None,
        chunker: TextChunker | None = None,
        store: ChromaEmbeddingStore | None = None,
    ) -> None:
        """등록 파이프라인의 의존성을 초기화합니다."""
        self.dispatcher = dispatcher or DocumentDispatcher()
        self.cleaner = cleaner or TextCleaner()
        self.chunker = chunker or TextChunker(CONFIG.chunk_size, CONFIG.chunk_overlap)
        self.store = store or ChromaEmbeddingStore()

    def index_file(self, file_path: str | Path) -> int:
        """파일을 등록하고 저장된 Chunk 개수를 반환합니다."""
        raw_path = copy_to_raw(Path(file_path).expanduser())
        documents = self.dispatcher.load(raw_path)
        all_chunks = []
        for document in documents:
            cleaned_text = self.cleaner.clean(document.text)
            cleaned_document = type(document)(
                source_path=document.source_path,
                text=cleaned_text,
                document_type=document.document_type,
                metadata=document.metadata,
            )
            all_chunks.extend(self.chunker.split(cleaned_document))
        return self.store.add_chunks(all_chunks)

    def index_paths(
        self,
        paths: list[str | Path],
        progress_callback: ProgressCallback | None = None,
        log_callback: LogCallback | None = None,
    ) -> IndexReport:
        """여러 파일 경로를 등록하고 처리 결과 보고서를 반환합니다."""
        files = self.collect_supported_files(paths)
        report = IndexReport(stored_location=CONFIG.chroma_dir)
        total = len(files)
        if total == 0:
            return report

        for index, file_path in enumerate(files, start=1):
            file_type = file_path.suffix.lower().lstrip(".").upper()
            try:
                if log_callback:
                    log_callback(f"처리 시작 [{file_type}]: {file_path}")
                created_chunks = self.index_file(file_path)
                report.processed_files += 1
                report.created_chunks += created_chunks
                if log_callback:
                    log_callback(f"처리 완료 [{file_type}]: {file_path} / Chunk {created_chunks}개")
            except Exception as exc:
                report.failed_files.append(f"{file_path} - {exc}")
                if log_callback:
                    log_callback(f"처리 실패 [{file_type}]: {file_path} / {exc}")
            if progress_callback:
                progress_callback(int(index / total * 100))
        return report

    def collect_supported_files(self, paths: list[str | Path]) -> list[Path]:
        """파일과 폴더 경로에서 지원 파일을 재귀적으로 수집합니다."""
        collected: dict[Path, None] = {}
        supported = set(CONFIG.supported_extensions)
        for raw_path in paths:
            path = Path(raw_path).expanduser()
            if path.is_dir():
                for child in sorted(path.rglob("*")):
                    if child.is_file() and child.suffix.lower() in supported:
                        collected[child.resolve()] = None
            elif path.is_file() and path.suffix.lower() in supported:
                collected[path.resolve()] = None
        return list(collected.keys())
