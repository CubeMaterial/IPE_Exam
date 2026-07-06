"""StudyRAG 전역 설정을 관리하는 모듈입니다."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class AppConfig:
    """애플리케이션 실행에 필요한 설정값을 담는 클래스입니다."""

    project_name: str = "StudyRAG"
    raw_data_dir: Path = BASE_DIR / "data" / "raw"
    processed_data_dir: Path = BASE_DIR / "data" / "processed"
    temp_data_dir: Path = BASE_DIR / "data" / "temp"
    chroma_dir: Path = BASE_DIR / "database" / "chroma"
    collection_name: str = "studyrag_documents"
    chunk_size: int = 900
    chunk_overlap: int = 150
    top_k: int = 5
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    embedding_model: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    ocr_languages: tuple[str, ...] = ("ko", "en")
    supported_extensions: tuple[str, ...] = (".pdf", ".txt", ".png", ".jpg", ".jpeg", ".zip")


CONFIG = AppConfig()


def ensure_directories(config: AppConfig = CONFIG) -> None:
    """프로젝트 실행에 필요한 디렉터리를 생성합니다."""
    # 로컬 프로젝트가 처음 실행될 때 필요한 저장소 폴더를 보장합니다.
    for directory in (
        config.raw_data_dir,
        config.processed_data_dir,
        config.temp_data_dir,
        config.chroma_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
