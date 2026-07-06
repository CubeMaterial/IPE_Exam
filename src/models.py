"""StudyRAG에서 공유하는 데이터 모델을 정의합니다."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Document:
    """원본 파일에서 추출한 텍스트 문서를 표현합니다."""

    source_path: Path
    text: str
    document_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentChunk:
    """벡터DB에 저장할 문서 조각을 표현합니다."""

    chunk_id: str
    source_path: Path
    chunk_number: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedChunk:
    """검색된 Chunk와 유사도 정보를 표현합니다."""

    chunk_id: str
    source_path: str
    chunk_number: int
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PastExamQuestion:
    """과년도 기출문제의 문제 단위 데이터를 표현합니다."""

    question_number: int
    body: str
    answer: str = ""
    explanation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
