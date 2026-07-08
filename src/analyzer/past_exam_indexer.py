"""과년도 기출문제 등록 파이프라인을 제공합니다."""

from __future__ import annotations

import json
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from config.config import CONFIG, ensure_directories
from src.analyzer.past_exam_classifier import PastExamClassifier
from src.analyzer.past_exam_parser import PastExamParser
from src.analyzer.post_validation import ClassificationValidator
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


@dataclass
class PastExamResetReport:
    """과년도 기출 초기화 결과를 표현합니다."""

    deleted_vector_chunks: int = 0
    reset_location: Path = CONFIG.past_exam_dir

    def to_message(self) -> str:
        """초기화 결과를 사용자에게 보여줄 문자열로 변환합니다."""
        return (
            "과년도 기출 데이터 초기화 완료\n"
            f"삭제된 벡터 Chunk 수: {self.deleted_vector_chunks}\n"
            f"초기화 위치: {self.reset_location}"
        )


class PastExamIndexer:
    """기출 파일 등록, 문제 분리, 자동 분류, 벡터 저장을 수행합니다."""

    _YEAR_PATTERN = re.compile(r"(20\d{2})\s*년?")
    _ROUND_PATTERN = re.compile(r"(?:제\s*)?([1-4])\s*회")

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
        self.validator = ClassificationValidator()

    def index_files(
        self,
        year: int,
        round_number: int,
        file_paths: list[str | Path],
        progress_callback: ProgressCallback | None = None,
        log_callback: LogCallback | None = None,
        use_llm_classification: bool = False,
    ) -> PastExamIndexReport:
        """선택한 과년도 기출 파일들을 등록합니다."""
        return self._index_files(
            file_paths=file_paths,
            identity_resolver=lambda path: (year, round_number),
            progress_callback=progress_callback,
            log_callback=log_callback,
            use_llm_classification=use_llm_classification,
        )

    def index_files_auto_metadata(
        self,
        file_paths: list[str | Path],
        progress_callback: ProgressCallback | None = None,
        log_callback: LogCallback | None = None,
        use_llm_classification: bool = False,
    ) -> PastExamIndexReport:
        """파일명 또는 본문에서 연도와 회차를 추출해 기출 파일들을 등록합니다."""
        return self._index_files(
            file_paths=file_paths,
            identity_resolver=self.extract_exam_identity,
            progress_callback=progress_callback,
            log_callback=log_callback,
            use_llm_classification=use_llm_classification,
        )

    def collect_supported_files(self, paths: list[str | Path]) -> list[Path]:
        """파일과 폴더 경로에서 기출 등록이 가능한 파일을 재귀적으로 수집합니다."""
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

    def reset_past_exam_data(self) -> PastExamResetReport:
        """과년도 기출 파일, JSON 인덱스, 벡터 Chunk를 초기화합니다."""
        deleted_chunks = self.store.delete_by_filter({"source_type": "past_exam"})
        if CONFIG.past_exam_dir.exists():
            shutil.rmtree(CONFIG.past_exam_dir)
        if CONFIG.exam_index_dir.exists():
            shutil.rmtree(CONFIG.exam_index_dir)
        ensure_directories()
        return PastExamResetReport(
            deleted_vector_chunks=deleted_chunks,
            reset_location=CONFIG.past_exam_dir,
        )

    def extract_exam_identity(self, path: str | Path) -> tuple[int, int]:
        """파일명이나 텍스트 본문에서 기출 연도와 회차를 추출합니다."""
        file_path = Path(path).expanduser()
        candidates = [file_path.name, file_path.stem]
        text = self._read_identity_text(file_path)
        if text:
            candidates.append(text[:4000])

        for candidate in candidates:
            normalized = unicodedata.normalize("NFC", candidate)
            year_match = self._YEAR_PATTERN.search(normalized)
            round_match = self._ROUND_PATTERN.search(normalized)
            if year_match and round_match:
                return int(year_match.group(1)), int(round_match.group(1))

        raise ValueError(f"파일명 또는 본문에서 연도/회차를 찾을 수 없습니다: {file_path}")

    def _index_files(
        self,
        file_paths: list[str | Path],
        identity_resolver: Callable[[Path], tuple[int, int]],
        progress_callback: ProgressCallback | None = None,
        log_callback: LogCallback | None = None,
        use_llm_classification: bool = False,
    ) -> PastExamIndexReport:
        """연도/회차 결정 전략을 받아 여러 기출 파일을 등록합니다."""
        ensure_directories()
        report = PastExamIndexReport(stored_location=CONFIG.past_exam_dir)
        records = self.load_index_records()
        structured_records_by_exam: dict[tuple[int, int], list[dict[str, Any]]] = {}
        total = len(file_paths)
        classifier = PastExamClassifier(use_llm=use_llm_classification)
        classification_mode = "LLM 자동 분류" if use_llm_classification else "빠른 키워드 분류"

        for index, file_path in enumerate(file_paths, start=1):
            path = Path(file_path).expanduser()
            try:
                year, round_number = identity_resolver(path)
                target_dir = CONFIG.past_exam_dir / str(year) / f"round_{round_number}"
                target_dir.mkdir(parents=True, exist_ok=True)
                report.stored_location = CONFIG.past_exam_dir
                if log_callback:
                    log_callback(f"기출 등록 시작: {path} ({year}년 {round_number}회 / {classification_mode})")
                copied_path = self._copy_to_exam_dir(path, target_dir)
                if log_callback:
                    self._log_missing_markdown_assets(copied_path, log_callback)
                documents = self.dispatcher.load(copied_path)
                chunks: list[DocumentChunk] = []
                for document in documents:
                    questions = self.parser.parse_questions(document.text)
                    if log_callback:
                        log_callback(f"문제 {len(questions)}개 분리 완료: {path.name}")
                    if not self.parser.has_question_markers(document.text):
                        report.parse_failed_files.append(str(path))
                        if log_callback:
                            log_callback(f"문제 단위 분리 실패: {path}")
                    for question_index, question in enumerate(questions, start=1):
                        if log_callback:
                            log_callback(f"문제 분류 중 [{question_index}/{len(questions)}]: {question.question_number}번")
                        classification = classifier.classify(question)
                        classification = self.validator.validate_classification(
                            classification,
                            {
                                "year": year,
                                "round": round_number,
                                "question_number": question.question_number,
                                "source_file": copied_path.name,
                                "body_preview": question.body[:200],
                            },
                        )
                        metadata = self._metadata(
                            year=year,
                            round_number=round_number,
                            source_file=copied_path,
                            question_number=question.question_number,
                            classification=classification,
                        )
                        text = self._question_text(question.body, question.answer, question.explanation)
                        chunks.append(self._chunk(copied_path, question.question_number, text, metadata))
                        index_record = self._index_record(metadata, copied_path)
                        records.append(index_record)
                        structured_records_by_exam.setdefault((year, round_number), []).append(
                            self._structured_record(question, metadata, copied_path)
                        )
                    report.parsed_questions += len(questions)
                if log_callback:
                    log_callback(f"벡터 저장 중: Chunk {len(chunks)}개")
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
        for (year, round_number), exam_records in structured_records_by_exam.items():
            self.save_exam_records(year, round_number, exam_records)
        return report

    def _read_identity_text(self, path: Path) -> str:
        """연도/회차 추출용으로 텍스트 파일 앞부분을 읽습니다."""
        if path.suffix.lower() not in {".txt", ".md"} or not path.exists():
            return ""

        for encoding in ("utf-8", "cp949", "euc-kr"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
            except OSError:
                return ""
        return ""

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

    def load_exam_records(self) -> list[dict[str, Any]]:
        """새 구조화 기출 JSON 인덱스를 모두 읽습니다."""
        if not CONFIG.exam_index_dir.exists():
            return []
        records: list[dict[str, Any]] = []
        for path in sorted(CONFIG.exam_index_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    records.append(
                        self.validator.validate_classification(
                            item,
                            {
                                "year": item.get("year", ""),
                                "round": item.get("round", ""),
                                "question_number": item.get("question_number", ""),
                                "source_file": item.get("source_file", ""),
                            },
                        )
                    )
        return records

    def save_exam_records(self, year: int, round_number: int, records: list[dict[str, Any]]) -> Path:
        """시험 회차별 구조화 기출 JSON을 저장합니다."""
        CONFIG.exam_index_dir.mkdir(parents=True, exist_ok=True)
        path = CONFIG.exam_index_dir / f"{year}_{round_number}.json"
        existing: list[dict[str, Any]] = []
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                existing = data if isinstance(data, list) else []
            except json.JSONDecodeError:
                existing = []
        existing.extend(records)
        path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _copy_to_exam_dir(self, path: Path, target_dir: Path) -> Path:
        """기출 원본 파일을 연도/회차 폴더로 복사합니다."""
        target = target_dir / f"{uuid4().hex}_{path.name}"
        shutil.copy2(path, target)
        self._copy_markdown_assets(path, target)
        return target

    def _copy_markdown_assets(self, source: Path, target: Path) -> None:
        """Markdown이 참조하는 로컬 이미지 assets를 함께 복사합니다."""
        if source.suffix.lower() != ".md":
            return
        try:
            text = source.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = source.read_text(encoding="cp949", errors="ignore")
        except OSError:
            return

        from src.loader.dispatcher import DocumentDispatcher

        for image_path in DocumentDispatcher()._markdown_image_paths(source, text):
            if not image_path.exists():
                continue
            try:
                relative = image_path.relative_to(source.parent)
            except ValueError:
                relative = Path(image_path.name)
            copied_asset = target.parent / relative
            copied_asset.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image_path, copied_asset)

    def _log_missing_markdown_assets(self, path: Path, log_callback: LogCallback) -> None:
        """Markdown이 참조하지만 존재하지 않는 이미지 파일을 로그에 출력합니다."""
        if path.suffix.lower() != ".md":
            return
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="cp949", errors="ignore")
        except OSError:
            return

        from src.loader.dispatcher import DocumentDispatcher

        missing = [image_path for image_path in DocumentDispatcher()._markdown_image_paths(path, text) if not image_path.exists()]
        if not missing:
            return
        log_callback("Markdown 참조 이미지가 없어 OCR을 수행할 수 없습니다.")
        for image_path in missing[:10]:
            log_callback(f"- 누락 이미지: {image_path}")

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
        secondary = classification.get("secondary", [])
        secondary_text = ", ".join(secondary) if isinstance(secondary, list) else str(secondary)
        language = classification.get("language") or ""
        if not language and is_code_file(source_file):
            language = detect_language_by_extension(source_file)
        return {
            "source_type": "past_exam",
            "exam_name": "정보처리기사 실기",
            "year": int(year),
            "round": int(round_number),
            "question_number": int(question_number),
            "subject": classification.get("subject", classification.get("category", "")),
            "category": classification.get("category", ""),
            "subcategory": classification.get("subcategory", classification.get("sub_category", "")),
            "sub_category": classification.get("subcategory", classification.get("sub_category", "")),
            "primary": classification.get("primary", classification.get("subcategory", "")),
            "secondary": secondary_text,
            "question_type": classification.get("question_type", ""),
            "language": language,
            "difficulty": classification.get("difficulty", ""),
            "concepts": keyword_text,
            "keywords": keyword_text,
            "intent": ", ".join(classification.get("intent", [])) if isinstance(classification.get("intent"), list) else str(classification.get("intent", "")),
            "mistakes": ", ".join(classification.get("mistakes", [])) if isinstance(classification.get("mistakes"), list) else str(classification.get("mistakes", "")),
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
            "subject": metadata["subject"],
            "category": metadata["category"],
            "subcategory": metadata["subcategory"],
            "sub_category": metadata["subcategory"],
            "primary": metadata.get("primary", metadata["subcategory"]),
            "secondary": [item.strip() for item in str(metadata.get("secondary", "")).split(",") if item.strip()],
            "question_type": metadata["question_type"],
            "language": metadata["language"],
            "difficulty": metadata["difficulty"],
            "keywords": keywords,
            "source_file": source_file.name,
        }

    def _structured_record(self, question, metadata: dict[str, Any], source_file: Path) -> dict[str, Any]:
        """요구사항에 맞는 문제 단위 구조화 JSON 레코드를 생성합니다."""
        return {
            "year": metadata["year"],
            "round": metadata["round"],
            "question_number": metadata["question_number"],
            "subject": metadata["subject"],
            "category": metadata["category"],
            "subcategory": metadata["subcategory"],
            "primary": metadata.get("primary", metadata["subcategory"]),
            "secondary": [item.strip() for item in str(metadata.get("secondary", "")).split(",") if item.strip()],
            "question_type": metadata["question_type"],
            "difficulty": metadata["difficulty"],
            "concepts": [item.strip() for item in str(metadata.get("concepts", "")).split(",") if item.strip()],
            "intent": [item.strip() for item in str(metadata.get("intent", "")).split(",") if item.strip()],
            "mistakes": [item.strip() for item in str(metadata.get("mistakes", "")).split(",") if item.strip()],
            "language": metadata["language"],
            "body": question.body,
            "answer": question.answer,
            "explanation": question.explanation,
            "page": question.metadata.get("page", ""),
            "source": question.metadata.get("source", source_file.name),
            "source_file": source_file.name,
        }
