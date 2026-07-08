"""StudyRAG 전역 설정을 관리하는 모듈입니다."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from src.utils.code_utils import CODE_EXTENSIONS


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent


def _get_int(name: str, default: int) -> int:
    """환경변수에서 정수 설정값을 안전하게 읽습니다."""
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _get_bool(name: str, default: bool) -> bool:
    """환경변수에서 불리언 설정값을 안전하게 읽습니다."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "y", "on"}


def _get_path(name: str, default: Path) -> Path:
    """환경변수에서 경로 설정값을 읽고 상대경로를 프로젝트 기준으로 변환합니다."""
    raw_value = os.getenv(name)
    path = Path(raw_value) if raw_value else default
    return path if path.is_absolute() else BASE_DIR / path


@dataclass
class AppConfig:
    """애플리케이션 실행에 필요한 설정값을 담는 클래스입니다."""

    project_name: str = "StudyRAG"
    raw_data_dir: Path = BASE_DIR / "data" / "raw"
    processed_data_dir: Path = BASE_DIR / "data" / "processed"
    temp_data_dir: Path = BASE_DIR / "data" / "temp"
    past_exam_dir: Path = BASE_DIR / "data" / "past_exams"
    past_exam_index_dir: Path = BASE_DIR / "data" / "past_exams" / "index"
    past_exam_index_file: Path = BASE_DIR / "data" / "past_exams" / "index" / "past_exam_index.json"
    exam_index_dir: Path = BASE_DIR / "data" / "exam_index"
    chroma_dir: Path = _get_path("CHROMA_DB_PATH", BASE_DIR / "database" / "chroma")
    collection_name: str = "studyrag_documents"
    chunk_size: int = _get_int("CHUNK_SIZE", 900)
    chunk_overlap: int = _get_int("CHUNK_OVERLAP", 150)
    code_chunk_size: int = _get_int("CODE_CHUNK_SIZE", 1600)
    top_k: int = 5
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    embedding_model: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    ocr_enabled: bool = _get_bool("OCR_ENABLED", True)
    ocr_languages: tuple[str, ...] = ("ko", "en")
    supported_extensions: tuple[str, ...] = (".pdf", ".txt", ".md", ".png", ".jpg", ".jpeg", ".zip") + CODE_EXTENSIONS


CONFIG = AppConfig()


def ensure_directories(config: AppConfig = CONFIG) -> None:
    """프로젝트 실행에 필요한 디렉터리를 생성합니다."""
    # 로컬 프로젝트가 처음 실행될 때 필요한 저장소 폴더를 보장합니다.
    for directory in (
        config.raw_data_dir,
        config.processed_data_dir,
        config.temp_data_dir,
        config.past_exam_dir,
        config.past_exam_index_dir,
        config.exam_index_dir,
        config.chroma_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def update_runtime_config(
    ollama_model: str,
    embedding_model: str,
    chunk_size: int,
    chunk_overlap: int,
    code_chunk_size: int,
    chroma_dir: Path,
    ocr_enabled: bool,
    config: AppConfig = CONFIG,
) -> None:
    """GUI 설정 화면에서 변경한 값을 현재 실행 설정에 반영합니다."""
    config.ollama_model = ollama_model
    config.embedding_model = embedding_model
    config.chunk_size = chunk_size
    config.chunk_overlap = chunk_overlap
    config.code_chunk_size = code_chunk_size
    config.chroma_dir = chroma_dir
    config.ocr_enabled = ocr_enabled
    ensure_directories(config)


def save_env_config(
    ollama_model: str,
    embedding_model: str,
    chunk_size: int,
    chunk_overlap: int,
    code_chunk_size: int,
    chroma_dir: Path,
    ocr_enabled: bool,
) -> Path:
    """GUI 설정값을 .env 파일에 저장합니다."""
    env_path = BASE_DIR / ".env"
    lines = [
        f"OLLAMA_BASE_URL={CONFIG.ollama_base_url}",
        f"OLLAMA_MODEL={ollama_model}",
        f"OLLAMA_EMBEDDING_MODEL={embedding_model}",
        f"CHUNK_SIZE={chunk_size}",
        f"CHUNK_OVERLAP={chunk_overlap}",
        f"CODE_CHUNK_SIZE={code_chunk_size}",
        f"CHROMA_DB_PATH={chroma_dir}",
        f"OCR_ENABLED={'true' if ocr_enabled else 'false'}",
    ]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env_path
