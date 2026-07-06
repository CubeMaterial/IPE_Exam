"""문서 등록 파이프라인을 제공합니다."""

from __future__ import annotations

from pathlib import Path

from config.config import CONFIG
from src.embedding.embedding import ChromaEmbeddingStore
from src.loader.dispatcher import DocumentDispatcher
from src.preprocess.chunker import TextChunker
from src.preprocess.cleaner import TextCleaner
from src.utils.file_utils import copy_to_raw


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
