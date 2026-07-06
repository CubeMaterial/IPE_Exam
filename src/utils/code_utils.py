"""소스코드 파일 확장자와 언어 판별 유틸리티를 제공합니다."""

from __future__ import annotations

from pathlib import Path


CODE_LANGUAGE_BY_EXTENSION: dict[str, str] = {
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".hpp": "C++",
    ".java": "Java",
    ".py": "Python",
    ".dart": "Dart",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".go": "Go",
    ".rs": "Rust",
    ".cs": "C#",
}


CODE_EXTENSIONS: tuple[str, ...] = tuple(CODE_LANGUAGE_BY_EXTENSION.keys())


LANGUAGE_ALIASES: dict[str, str] = {
    "c": "C",
    "c언어": "C",
    "c language": "C",
    "cpp": "C++",
    "c++": "C++",
    "java": "Java",
    "자바": "Java",
    "python": "Python",
    "파이썬": "Python",
    "dart": "Dart",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "kotlin": "Kotlin",
    "kt": "Kotlin",
    "swift": "Swift",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "rs": "Rust",
    "c#": "C#",
    "csharp": "C#",
}


CODE_QUERY_KEYWORDS: tuple[str, ...] = (
    "코드",
    "소스",
    "프로그램",
    "함수",
    "클래스",
    "메서드",
    "메소드",
    "포인터",
    "배열",
    "반복문",
    "상속",
    "슬라이싱",
    "출력",
    "컴파일",
)


def is_code_extension(extension: str) -> bool:
    """확장자가 지원하는 소스코드 파일인지 확인합니다."""
    return extension.lower() in CODE_LANGUAGE_BY_EXTENSION


def is_code_file(path: Path) -> bool:
    """파일 경로가 지원하는 소스코드 파일인지 확인합니다."""
    return is_code_extension(path.suffix)


def detect_language_by_extension(path: Path) -> str:
    """파일 확장자로 코드 언어를 판별합니다."""
    return CODE_LANGUAGE_BY_EXTENSION.get(path.suffix.lower(), "Unknown")


def detect_language_in_query(question: str) -> str | None:
    """질문 문장에서 우선 검색할 코드 언어를 추정합니다."""
    lowered = question.lower()
    for keyword, language in LANGUAGE_ALIASES.items():
        if keyword in lowered:
            return language
    return None


def is_code_related_query(question: str) -> bool:
    """질문이 코드 검색과 관련 있는지 추정합니다."""
    lowered = question.lower()
    return detect_language_in_query(question) is not None or any(keyword in lowered for keyword in CODE_QUERY_KEYWORDS)
