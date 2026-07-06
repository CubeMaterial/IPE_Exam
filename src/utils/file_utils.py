"""파일 처리 공통 유틸리티를 제공합니다."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from config.config import CONFIG
from src.utils.exceptions import UnsupportedFileError


def normalize_extension(path: Path) -> str:
    """파일 확장자를 소문자로 정규화합니다."""
    return path.suffix.lower()


def validate_supported_file(path: Path) -> None:
    """지원하는 파일 형식인지 검사합니다."""
    # 등록 단계에서 허용되지 않는 형식을 조기에 차단합니다.
    if normalize_extension(path) not in CONFIG.supported_extensions:
        raise UnsupportedFileError(f"지원하지 않는 파일 형식입니다: {path.suffix}")


def copy_to_raw(path: Path) -> Path:
    """원본 파일을 raw 폴더로 복사하고 복사된 경로를 반환합니다."""
    validate_supported_file(path)
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    target = CONFIG.raw_data_dir / f"{uuid4().hex}_{path.name}"
    shutil.copy2(path, target)
    return target


def write_processed_text(source_path: Path, text: str, suffix: str = ".txt") -> Path:
    """추출 또는 OCR 결과 텍스트를 processed 폴더에 저장합니다."""
    target = CONFIG.processed_data_dir / f"{source_path.stem}{suffix}"
    target.write_text(text, encoding="utf-8")
    return target
