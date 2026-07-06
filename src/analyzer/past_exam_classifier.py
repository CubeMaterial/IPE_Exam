"""LLM 기반 과년도 기출문제 자동 분류기를 제공합니다."""

from __future__ import annotations

import json
import re
from typing import Any

from src.llm.ollama_client import OllamaClient
from src.models import PastExamQuestion
from src.utils.code_utils import detect_language_in_query


PAST_EXAM_CLASSIFIER_PROMPT = """
당신은 정보처리기사 실기 기출문제 분류 전문가입니다.
반드시 JSON 하나만 출력하세요.
필드: category, sub_category, question_type, language, difficulty, keywords, intent, wrong_points
category 후보:
요구사항 확인, 화면 설계, 데이터 입출력 구현, 통합 구현, 인터페이스 구현, 프로그래밍 언어 활용,
SQL 응용, 서버 프로그램 구현, 소프트웨어 개발 보안 구축, 애플리케이션 테스트 관리,
응용 SW 기초 기술 활용, 제품 소프트웨어 패키징
question_type 후보:
개념 서술, 빈칸, 용어, 코드 출력, SQL 작성, SQL 결과, UML, 계산, 보안 공격기법, 네트워크, 운영체제
""".strip()


class PastExamClassifier:
    """기출문제를 과목, 유형, 난이도, 키워드로 자동 분류합니다."""

    def __init__(self, llm: OllamaClient | None = None) -> None:
        """LLM 의존성을 초기화합니다."""
        self.llm = llm or OllamaClient()

    def classify(self, question: PastExamQuestion) -> dict[str, Any]:
        """기출문제 하나를 분류하고 메타데이터 딕셔너리를 반환합니다."""
        try:
            response = self.llm.generate(PAST_EXAM_CLASSIFIER_PROMPT, question.body[:4000])
            parsed = self._parse_json(response)
            return self._normalize(parsed, question.body)
        except Exception:
            return self._fallback(question.body)

    def _parse_json(self, response: str) -> dict[str, Any]:
        """LLM 응답에서 JSON 객체를 추출합니다."""
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if not match:
            raise ValueError("분류 JSON을 찾을 수 없습니다.")
        parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            raise ValueError("분류 결과가 JSON 객체가 아닙니다.")
        return parsed

    def _normalize(self, parsed: dict[str, Any], body: str) -> dict[str, Any]:
        """분류 결과의 누락 필드를 기본값으로 보정합니다."""
        keywords = parsed.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [item.strip() for item in keywords.split(",") if item.strip()]
        language = parsed.get("language") or detect_language_in_query(body) or ""
        return {
            "category": str(parsed.get("category") or self._guess_category(body)),
            "sub_category": str(parsed.get("sub_category") or self._guess_sub_category(body)),
            "question_type": str(parsed.get("question_type") or self._guess_question_type(body)),
            "language": str(language),
            "difficulty": str(parsed.get("difficulty") or "중"),
            "keywords": keywords or self._guess_keywords(body),
            "intent": str(parsed.get("intent") or ""),
            "wrong_points": str(parsed.get("wrong_points") or ""),
        }

    def _fallback(self, body: str) -> dict[str, Any]:
        """LLM 분류 실패 시 키워드 기반 기본 분류를 생성합니다."""
        return {
            "category": self._guess_category(body),
            "sub_category": self._guess_sub_category(body),
            "question_type": self._guess_question_type(body),
            "language": detect_language_in_query(body) or "",
            "difficulty": "중",
            "keywords": self._guess_keywords(body),
            "intent": "과거 기출 기반 자동 분류가 필요합니다.",
            "wrong_points": "",
        }

    def _guess_category(self, body: str) -> str:
        """문제 본문 키워드로 과목을 추정합니다."""
        lowered = body.lower()
        if any(keyword in lowered for keyword in ("select", "join", "group by", "having", "sql")):
            return "SQL 응용"
        if any(keyword in lowered for keyword in ("int ", "class ", "public", "def ", "포인터", "배열")):
            return "프로그래밍 언어 활용"
        if any(keyword in body for keyword in ("공격", "보안", "암호", "취약점")):
            return "소프트웨어 개발 보안 구축"
        if any(keyword in body for keyword in ("TCP", "IP", "프로토콜", "운영체제", "스케줄링")):
            return "응용 SW 기초 기술 활용"
        return "응용 SW 기초 기술 활용"

    def _guess_sub_category(self, body: str) -> str:
        """문제 본문 키워드로 세부 유형을 추정합니다."""
        language = detect_language_in_query(body)
        if "포인터" in body:
            return "C 포인터"
        if "상속" in body or "오버라이딩" in body:
            return "Java 상속/오버라이딩"
        if "group by" in body.lower() or "having" in body.lower():
            return "SQL GROUP BY/HAVING"
        if language:
            return f"{language} 코드"
        return "기본 개념"

    def _guess_question_type(self, body: str) -> str:
        """문제 본문 키워드로 문제 유형을 추정합니다."""
        lowered = body.lower()
        if any(keyword in lowered for keyword in ("출력", "실행 결과", "print", "printf", "system.out")):
            return "코드 출력"
        if "select" in lowered:
            return "SQL 결과"
        if "빈칸" in body or "괄호" in body:
            return "빈칸"
        return "개념 서술"

    def _guess_keywords(self, body: str) -> list[str]:
        """문제 본문에서 대표 키워드를 추정합니다."""
        candidates = ["포인터", "배열", "상속", "오버라이딩", "JOIN", "GROUP BY", "HAVING", "보안", "네트워크"]
        return [keyword for keyword in candidates if keyword.lower() in body.lower()][:5]
