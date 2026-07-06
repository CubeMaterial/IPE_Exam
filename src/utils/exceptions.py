"""StudyRAG 전용 예외 클래스를 정의합니다."""


class StudyRAGError(Exception):
    """StudyRAG 기본 예외입니다."""


class UnsupportedFileError(StudyRAGError):
    """지원하지 않는 파일 형식 예외입니다."""


class DocumentLoadError(StudyRAGError):
    """문서 읽기 실패 예외입니다."""


class OCRError(StudyRAGError):
    """OCR 처리 실패 예외입니다."""


class LLMError(StudyRAGError):
    """LLM 또는 임베딩 호출 실패 예외입니다."""


class VectorStoreError(StudyRAGError):
    """벡터DB 처리 실패 예외입니다."""
