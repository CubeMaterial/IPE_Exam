"""Concept Dictionary를 로드하고 문제 본문에서 개념을 탐지합니다."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from config.config import BASE_DIR


class ConceptDictionary:
    """분석에 사용할 개념 사전을 JSON 파일로 관리합니다."""

    CATEGORY_FILES = {
        "C": "c.json",
        "Java": "java.json",
        "Python": "python.json",
        "SQL": "sql.json",
        "네트워크": "network.json",
        "운영체제": "os.json",
        "보안": "security.json",
        "DB": "db.json",
        "디자인패턴": "design_pattern.json",
        "테스트": "testing.json",
        "소프트웨어설계": "software_design.json",
        "인터페이스": "interface.json",
        "UML": "uml.json",
    }
    CONCEPT_PRIORITY = {
        "C": ["포인터", "증감연산", "배열", "반복문", "문자열", "구조체", "재귀", "함수", "형변환"],
        "Java": ["상속", "오버라이딩", "인터페이스", "추상클래스", "컬렉션", "예외처리", "static", "클래스"],
        "Python": ["슬라이싱", "딕셔너리", "리스트", "튜플", "Set", "Class", "Lambda", "Range"],
        "SQL": ["JOIN", "INNER JOIN", "OUTER JOIN", "GROUP BY", "HAVING", "SUBQUERY", "집계함수", "제약조건", "VIEW", "INDEX", "DDL", "DML", "DCL", "TCL", "INSERT", "UPDATE", "DELETE", "SELECT"],
    }

    def __init__(self, directory: Path | None = None) -> None:
        """사전 디렉터리를 초기화합니다."""
        self.directory = directory or BASE_DIR / "config" / "concept_dictionary"

    def load(self, category: str | None = None) -> dict[str, list[str]]:
        """카테고리별 또는 전체 Concept Dictionary를 읽습니다."""
        if category:
            filename = self.CATEGORY_FILES.get(category)
            if not filename:
                return {}
            return self._read_file(self.directory / filename)
        merged: dict[str, list[str]] = {}
        for path in sorted(self.directory.glob("*.json")):
            merged.update(self._read_file(path))
        return merged

    def save(self, filename: str, data: dict[str, list[str]]) -> Path:
        """사전 JSON 파일을 저장합니다."""
        path = self.directory / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def filenames(self) -> list[str]:
        """편집 가능한 사전 파일 목록을 반환합니다."""
        return sorted(path.name for path in self.directory.glob("*.json"))

    def detect(self, text: str, category: str = "", language: str = "") -> list[str]:
        """본문에서 Concept Dictionary 기반 개념을 탐지합니다."""
        dictionary = self.load(category) or self.load(language)
        if not dictionary:
            dictionary = self.load()
        lowered = text.lower()
        detected = []
        for concept, keywords in dictionary.items():
            if self._contains_concept(lowered, concept, keywords):
                detected.append(concept)
        return self._sort_detected(detected, category or language)

    def primary_secondary(self, text: str, category: str = "", language: str = "") -> tuple[str, list[str]]:
        """탐지된 개념을 primary/secondary로 분리합니다."""
        detected = self.detect(text, category=category, language=language)
        if not detected:
            return "미분류", []
        return detected[0], detected[1:]

    def _read_file(self, path: Path) -> dict[str, list[str]]:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return {
            str(key): [str(item) for item in value]
            for key, value in data.items()
            if isinstance(value, list)
        }

    def _contains_concept(self, lowered_text: str, concept: str, keywords: list[str]) -> bool:
        values = [concept, *keywords]
        for value in values:
            lowered_value = value.lower()
            if not lowered_value:
                continue
            if re.search(r"[a-z0-9_]", lowered_value):
                if re.search(rf"(?<![a-z0-9_]){re.escape(lowered_value)}(?![a-z0-9_])", lowered_text):
                    return True
            elif lowered_value in lowered_text:
                return True
        return False

    def _sort_detected(self, detected: list[str], category: str) -> list[str]:
        priority = self.CONCEPT_PRIORITY.get(category, [])
        if not priority:
            return detected
        order = {concept: index for index, concept in enumerate(priority)}
        return sorted(detected, key=lambda concept: order.get(concept, len(priority)))
