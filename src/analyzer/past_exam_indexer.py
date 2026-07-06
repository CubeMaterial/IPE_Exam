"""과년도 기출문제 등록 파이프라인을 제공합니다."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from config.config import CONFIG, ensure_directories
from src.analyzer.past_exam_classifier import PastExamClassifier
from src.analyzer.past_exam_parser import PastExamParser
from src.embedding.embedding import ChromaEmbeddingStore
from src.loader.dispatcher import DocumentDispatcher
from src.models import DocumentChunk
from src.preprocess.cleaner import TextCleaner
from src.utils.code_utils import detect_language_by_extension, is_code_file
from src.utils.file_utils import normalize_extension


ProgressCallback = Callable[[int], None]
LogCallback = Callable[[str], None]


@dataclass
class PastExamIndexReport:
    """기출 등록 결과를 표현합니다."""

    processed_files: int = 0
    parsed_questions: int = 0
    created_chunks: int = 0
    failed_files: list[str] = field(default_factory=list)
    parse_failed_files: list[str] = field(default_factory=list)
    stored_location: Path = CONFIG.past_exam_dir

    def to_message(self) -> str:
        """등록 결과를 사용자에게 보여줄 문자열로 변환합니다."""
        failures = "\n".join(f"- {item}" for item in self.failed_files) or "없음"
        parse_failures = "\n".join(f"- {item}" for item in self.parse_failed_files) or "없음"
        return (
            f"처리된 파일 수: {self.processed_files}\n"
            f"분리된 문제 수: {self.parsed_questions}\n"
            f"생성된 Chunk 수: {self.created_chunks}\n"
            f"저장 위치: {self.stored_location}\n"
            f"문제 단위 분리 실패:\n{parse_failures}\n"
            f"실패 파일 목록:\n{failures}"
        )


class PastExamIndexer:
    """기출 파일 등록, 문제 분리, 자동 분류, 벡터 저장을 수행합니다."""

    def __init__(
        self,
        dispatcher: DocumentDispatcher | None = None,
        parser: PastExamParser | None = None,
        classifier: PastExamClassifier | None = None,
        store: ChromaEmbeddingStore | None = None,
        cleaner: TextCleaner | None = None,
    ) -> None:
        """기출 등록 파이프라인 의존성을 초기화합니다."""
        self.dispatcher = dispatcher or DocumentDispatcher()
        self.parser = parser or PastExamParser()
        self.classifier = classifier or PastExamClassifier()
        self.store = store or ChromaEmbeddingStore()
        self.cleaner = cleaner or TextCleaner()

    def index_files(
        self,
        year: int,
        round_number: int,
        file_paths: list[str | Path],
        progress_callback: ProgressCallback | None = None,
        log_callback: LogCallback | None = None,
    ) -> PastExamIndexReport:
        """선택한 과년도 기출 파일들을 등록합니다."""
        ensure_directories()
        target_dir = CONFIG.past_exam_dir / str(year) / f"round_{round_number}"
        target_dir.mkdir(parents=True, exist_ok=True)
        report = PastExamIndexReport(stored_location=target_dir)
        records = self.load_index_records()
        total = len(file_paths)

        for index, file_path in enumerate(file_paths, start=1):
            path = Path(file_path).expanduser()
            try:
                if log_callback:
                    log_callback(f"기출 등록 시작: {path}")
                copied_path = self._copy_to_exam_dir(path, target_dir)
                documents = self.dispatcher.load(copied_path)
                chunks: list[DocumentChunk] = []
                for document in documents:
                    questions = self.parser.parse_questions(document.text)
                    if not self.parser.has_question_markers(document.text):
                        report.parse_failed_files.append(str(path))
                        if log_callback:
                            log_callback(f"문제 단위 분리 실패: {path}")
                    for question in questions:
                        classification = self.classifier.classify(question)
                        metadata = self._metadata(
                            year=year,
                            round_number=round_number,
                            source_file=copied_path,
                            question_number=question.question_number,
                            classification=classification,
                        )
                        text = self._question_text(question.body, question.answer, question.explanation)
                        chunks.append(self._chunk(copied_path, question.question_number, text, metadata))
                        records.append(self._index_record(metadata, copied_path))
                    report.parsed_questions += len(questions)
                report.created_chunks += self.store.add_chunks(chunks)
                report.processed_files += 1
                if log_callback:
                    log_callback(f"기출 등록 완료: {path} / 문제 {len(chunks)}개")
            except Exception as exc:
                report.failed_files.append(f"{path} - {exc}")
                if log_callback:
                    log_callback(f"기출 등록 실패: {path} / {exc}")
            if progress_callback and total:
                progress_callback(int(index / total * 100))

        self.save_index_records(records)
        return report

    def load_index_records(self) -> list[dict[str, Any]]:
        """저장된 기출 JSON 인덱스를 읽습니다."""
        if not CONFIG.past_exam_index_file.exists():
            return []
        try:
            data = json.loads(CONFIG.past_exam_index_file.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    def save_index_records(self, records: list[dict[str, Any]]) -> None:
        """기출 JSON 인덱스를 저장합니다."""
        CONFIG.past_exam_index_dir.mkdir(parents=True, exist_ok=True)
        CONFIG.past_exam_index_file.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _copy_to_exam_dir(self, path: Path, target_dir: Path) -> Path:
        """기출 원본 파일을 연도/회차 폴더로 복사합니다."""
        target = target_dir / f"{uuid4().hex}_{path.name}"
        shutil.copy2(path, target)
        return target

    def _metadata(
        self,
        year: int,
        round_number: int,
        source_file: Path,
        question_number: int,
        classification: dict[str, Any],
    ) -> dict[str, Any]:
        """ChromaDB에 저장할 기출 메타데이터를 생성합니다."""
        keywords = classification.get("keywords", [])
        keyword_text = ", ".join(keywords) if isinstance(keywords, list) else str(keywords)
        language = classification.get("language") or ""
        if not language and is_code_file(source_file):
            language = detect_language_by_extension(source_file)
        return {
            "source_type": "past_exam",
            "exam_name": "정보처리기사 실기",
            "year": int(year),
            "round": int(round_number),
            "question_number": int(question_number),
            "category": classification.get("category", ""),
            "sub_category": classification.get("sub_category", ""),
            "question_type": classification.get("question_type", ""),
            "language": language,
            "difficulty": classification.get("difficulty", "중"),
            "keywords": keyword_text,
            "intent": classification.get("intent", ""),
            "wrong_points": classification.get("wrong_points", ""),
            "source_file": source_file.name,
            "extension": normalize_extension(source_file),
        }

    def _chunk(self, source_file: Path, question_number: int, text: str, metadata: dict[str, Any]) -> DocumentChunk:
        """기출문제 하나를 ChromaDB 저장용 Chunk로 변환합니다."""
        chunk_id = f"past_exam_{metadata['year']}_{metadata['round']}_{question_number}_{uuid4().hex[:8]}"
        return DocumentChunk(
            chunk_id=chunk_id,
            source_path=source_file,
            chunk_number=question_number,
            text=text,
            metadata=metadata | {"document_type": "past_exam"},
        )

    def _question_text(self, body: str, answer: str, explanation: str) -> str:
        """문제, 정답, 해설을 하나의 검색 텍스트로 구성합니다."""
        parts = [f"문제:\n{self.cleaner.clean(body)}"]
        if answer:
            parts.append(f"정답:\n{self.cleaner.clean(answer)}")
        if explanation:
            parts.append(f"해설:\n{self.cleaner.clean(explanation)}")
        return "\n\n".join(parts)

    def _index_record(self, metadata: dict[str, Any], source_file: Path) -> dict[str, Any]:
        """JSON 인덱스에 저장할 레코드를 생성합니다."""
        keywords = [item.strip() for item in str(metadata.get("keywords", "")).split(",") if item.strip()]
        return {
            "year": metadata["year"],
            "round": metadata["round"],
            "question_number": metadata["question_number"],
            "category": metadata["category"],
            "sub_category": metadata["sub_category"],
            "question_type": metadata["question_type"],
            "language": metadata["language"],
            "difficulty": metadata["difficulty"],
            "keywords": keywords,
            "source_file": source_file.name,
        }
