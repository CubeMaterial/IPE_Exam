"""LLM 기반 과년도 기출문제 자동 분류기를 제공합니다."""

from __future__ import annotations

import json
import re
from typing import Any

from src.analyzer.concept_dictionary import ConceptDictionary
from src.analyzer.post_validation import ClassificationValidator, UNCLASSIFIED
from src.llm.ollama_client import OllamaClient
from src.models import PastExamQuestion
from src.utils.code_utils import detect_language_in_query


PAST_EXAM_CLASSIFIER_PROMPT = """
당신은 정보처리기사 실기 기출문제 분류 전문가입니다.
반드시 JSON 하나만 출력하세요.
필드: subject, category, subcategory, primary, secondary, question_type, difficulty, concepts, intent, mistakes
과목(subject), 카테고리(category), 문제 유형(question_type), 세부 유형(subcategory)을 절대 섞지 마세요.
language는 C, Java, Python, SQL, 기타 중 하나만 사용하세요.
TypeScript, JavaScript, Dart, Kotlin 등은 정보처리기사 실기 과년도 분석 언어로 분류하지 말고 기타로 분류하세요.
category는 아래 후보 중 하나만 사용하세요. 판단이 어려워도 기타를 쓰지 말고 가장 가까운 후보를 고르세요.
운영체제, 네트워크, DB, SQL, C, Java, Python, 자료구조, 보안, 인터페이스, UML, 디자인패턴, 테스트, 프로젝트관리, 신기술, 알고리즘, 데이터모델링, 소프트웨어설계
subcategory는 "기초기술", "일반개념", "코드"처럼 넓게 쓰지 말고 포인터, JOIN, 프로세스처럼 구체 개념으로 쓰세요.
subcategory는 반드시 정의된 Tree의 값 중 하나를 선택하세요. Tree에 없으면 미분류로 저장하세요.
primary는 대표 개념 하나, secondary는 같은 문제에 함께 등장한 부개념 배열입니다.
subject 후보:
요구사항 확인, 화면 설계, 데이터 입출력 구현, 통합 구현, 인터페이스 구현, 프로그래밍 언어 활용,
SQL 응용, 서버 프로그램 구현, 소프트웨어 개발 보안 구축, 애플리케이션 테스트 관리,
응용 SW 기초 기술 활용, 제품 소프트웨어 패키징
question_type 후보:
개념 서술, 빈칸, 용어, 코드 출력, SQL 작성, SQL 결과, UML, 계산, 보안 공격기법, 네트워크, 운영체제
""".strip()

PAST_EXAM_RECLASSIFY_PROMPT = """
이전 분류에서 category 또는 subcategory가 너무 넓었습니다.
반드시 JSON 하나만 출력하세요.
category 후보:
운영체제, 네트워크, DB, SQL, C, Java, Python, 자료구조, 보안, 인터페이스, UML, 디자인패턴, 테스트, 프로젝트관리, 신기술, 알고리즘, 데이터모델링, 소프트웨어설계
subcategory는 구체 개념만 사용하세요. "기타", "일반 개념", "기초 기술", "코드" 금지.
판단이 어려우면 문제 본문에서 가장 핵심이 되는 개념 하나를 subcategory로 선택하세요.
필드: subject, category, subcategory, primary, secondary, question_type, concepts, intent, mistakes
""".strip()


class PastExamClassifier:
    """기출문제를 과목, 유형, 난이도, 키워드로 자동 분류합니다."""

    CATEGORIES = {
        "요구사항 확인",
        "화면 설계",
        "데이터 입출력 구현",
        "통합 구현",
        "인터페이스 구현",
        "프로그래밍 언어 활용",
        "SQL 응용",
        "서버 프로그램 구현",
        "소프트웨어 개발 보안 구축",
        "애플리케이션 테스트 관리",
        "응용 SW 기초 기술 활용",
        "제품 소프트웨어 패키징",
    }
    QUESTION_TYPES = {
        "개념 서술",
        "용어",
        "빈칸",
        "코드 출력",
        "SQL 작성",
        "SQL 결과",
        "UML",
        "계산",
        "보안 공격기법",
        "네트워크",
        "운영체제",
    }
    ANALYSIS_CATEGORIES = {
        "운영체제",
        "네트워크",
        "DB",
        "소프트웨어설계",
        "SQL",
        "C",
        "Java",
        "Python",
        "자료구조",
        "보안",
        "인터페이스",
        "UML",
        "디자인패턴",
        "테스트",
        "프로젝트관리",
        "신기술",
        "알고리즘",
        "데이터모델링",
        "미분류",
    }
    CATEGORY_SUBCATEGORIES = {
        "운영체제": {"프로세스", "스레드", "PCB", "교착상태", "세마포어", "뮤텍스", "스케줄링", "메모리관리", "페이지교체"},
        "네트워크": {"OSI", "TCP", "UDP", "TCP/IP", "HTTP", "HTTPS", "DNS", "DHCP", "IPv4", "IPv6", "ARP", "ICMP", "NAT", "라우팅", "3-way Handshake"},
        "C": {"포인터", "배열", "문자열", "함수", "재귀", "구조체", "증감연산", "반복문", "형변환"},
        "Java": {"클래스", "상속", "오버라이딩", "인터페이스", "추상클래스", "컬렉션", "예외처리", "static"},
        "Python": {"리스트", "슬라이싱", "딕셔너리", "튜플", "Set", "Class", "Lambda", "Range"},
        "SQL": {"SELECT", "INSERT", "UPDATE", "DELETE", "JOIN", "INNER JOIN", "OUTER JOIN", "GROUP BY", "HAVING", "SUBQUERY", "VIEW", "INDEX", "DDL", "DML", "DCL", "TCL", "제약조건", "집계함수"},
        "DB": {"Cardinality", "Degree", "정규화", "ERD", "무결성", "트랜잭션"},
        "데이터모델링": {"ERD", "정규화", "관계", "식별자", "속성"},
        "소프트웨어설계": {"응집도", "결합도", "GoF", "MVC", "설계원칙", "SOLID"},
        "보안": {"ISMS", "SQL Injection", "XSS", "CSRF", "Buffer Overflow", "AES", "RSA", "SHA", "접근통제", "인증", "방화벽"},
        "UML": {"UseCase", "Class Diagram", "Sequence Diagram", "Activity Diagram"},
        "디자인패턴": {"Singleton", "Factory", "Observer", "Strategy", "Builder", "Adapter", "MVC"},
        "인터페이스": {"REST", "JSON", "XML", "AJAX", "OpenAPI", "API", "EAI", "ESB"},
        "프로젝트관리": {"일정관리", "위험관리", "형상관리", "WBS"},
        "테스트": {"테스트 커버리지", "화이트박스", "블랙박스", "스텁", "드라이버"},
        "자료구조": {"스택", "큐", "트리", "그래프", "해시"},
        "알고리즘": {"정렬", "탐색", "재귀", "시간복잡도"},
        "신기술": {"클라우드", "IoT", "빅데이터", "AI", "블록체인"},
    }
    GENERIC_SUBCATEGORIES = {
        "",
        "기타",
        "기타 코드",
        "기본 개념",
        "일반 개념",
        "일반개념",
        "기초 기술",
        "기초기술",
        "코드",
        "문제",
        "C 코드",
        "Java 코드",
        "Python 코드",
        "SQL 작성",
    }
    EXAM_LANGUAGES = {"C", "Java", "Python", "SQL", "기타"}
    NON_EXAM_LANGUAGE_KEYWORDS = {
        "typescript",
        "javascript",
        "dart",
        "kotlin",
        "swift",
        "golang",
        "rust",
        "c#",
        "c++",
    }

    def __init__(
        self,
        llm: OllamaClient | None = None,
        use_llm: bool = True,
        concept_dictionary: ConceptDictionary | None = None,
    ) -> None:
        """LLM 의존성을 초기화합니다."""
        self.llm = llm or OllamaClient()
        self.use_llm = use_llm
        self.concept_dictionary = concept_dictionary or ConceptDictionary()
        self.validator = ClassificationValidator()

    def classify(self, question: PastExamQuestion) -> dict[str, Any]:
        """기출문제 하나를 분류하고 메타데이터 딕셔너리를 반환합니다."""
        if not self.use_llm:
            return self._fallback(question.body)

        try:
            response = self.llm.generate(PAST_EXAM_CLASSIFIER_PROMPT, question.body[:4000])
            parsed = self._parse_json(response)
            normalized = self._normalize(parsed, question.body)
            if normalized["category"] == "미분류" or normalized["subcategory"] in self.GENERIC_SUBCATEGORIES:
                retry = self.llm.generate(PAST_EXAM_RECLASSIFY_PROMPT, question.body[:4000])
                retry_parsed = self._parse_json(retry)
                normalized = self._normalize(retry_parsed, question.body)
            return self.validator.validate_classification(normalized)
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
        subject = self._normalize_category(str(parsed.get("subject") or parsed.get("category") or ""), body)
        question_type = self._normalize_question_type(str(parsed.get("question_type") or ""), body)
        language = self._normalize_language(str(parsed.get("language") or ""), body)
        category = self._normalize_analysis_category(str(parsed.get("category") or ""), body, subject, language)
        detected_primary, detected_secondary = self.concept_dictionary.primary_secondary(
            body,
            category=category,
            language=language,
        )
        parsed_primary = str(parsed.get("primary") or "")
        parsed_secondary = self._as_list(parsed.get("secondary"))
        subcategory = self._normalize_sub_category(
            str(parsed.get("subcategory") or parsed.get("sub_category") or ""),
            body,
            category,
            question_type,
            language,
        )
        primary = self._coerce_subcategory(category, parsed_primary) if parsed_primary else detected_primary
        if primary == "미분류":
            primary = subcategory
        secondary = self._normalize_secondary(category, [*parsed_secondary, *detected_secondary], primary)
        subcategory = primary
        concepts = self._ordered_unique([primary, *secondary, *self._as_list(parsed.get("concepts") or parsed.get("keywords")), *self._guess_keywords(body)])
        intent = self._as_list(parsed.get("intent")) or self._guess_intent(body, subcategory, question_type)
        mistakes = self._as_list(parsed.get("mistakes") or parsed.get("wrong_points")) or self._guess_mistakes(body, subcategory)
        return {
            "subject": subject,
            "category": category,
            "subcategory": subcategory,
            "sub_category": subcategory,
            "primary": primary,
            "secondary": secondary,
            "question_type": question_type,
            "language": language,
            "difficulty": "",
            "concepts": concepts,
            "keywords": concepts,
            "intent": intent,
            "mistakes": mistakes,
            "wrong_points": ", ".join(mistakes),
        }

    def _fallback(self, body: str) -> dict[str, Any]:
        """LLM 분류 실패 시 확실한 키워드만 재분류하고, 아니면 미분류로 저장합니다."""
        keyword_classification = self._keyword_reclassify(body)
        if keyword_classification is not None:
            return self.validator.validate_classification(keyword_classification)
        return self._unclassified_result(
            question_type=self._guess_question_type(body),
            language=self._normalize_language("", body),
        )

    def _keyword_reclassify(self, body: str) -> dict[str, Any] | None:
        """본문 키워드 기반으로 확실한 경우만 재분류합니다."""
        lowered = body.lower()
        rules: list[tuple[str, str, str, tuple[str, ...]]] = [
            ("서버 프로그램 구현", "소프트웨어설계", "응집도", ("응집도", "cohesion")),
            ("서버 프로그램 구현", "소프트웨어설계", "결합도", ("결합도", "coupling")),
            ("데이터 입출력 구현", "DB", "Cardinality", ("cardinality", "카디널리티")),
            ("데이터 입출력 구현", "DB", "Degree", ("degree", "차수")),
            ("데이터 입출력 구현", "DB", "정규화", ("정규형", "정규화")),
            ("데이터 입출력 구현", "DB", "무결성", ("제약조건", "릴레이션", "무결성")),
            ("SQL 응용", "SQL", "JOIN", ("조인", "join", "equi join", "natural join")),
            ("응용 SW 기초 기술 활용", "네트워크", "TCP/IP", ("패킷 교환", "연결형", "비연결형", "데이터그램", "가상회선")),
            ("응용 SW 기초 기술 활용", "네트워크", "ICMP", ("crc", "해밍", "패리티")),
            ("소프트웨어 개발 보안 구축", "보안", "악성코드", ("악성코드", "스케어웨어", "랜섬웨어")),
            ("소프트웨어 개발 보안 구축", "보안", "인증", ("oauth", "인증", "접근")),
            ("소프트웨어 개발 보안 구축", "보안", "ISMS", ("isms",)),
            ("응용 SW 기초 기술 활용", "운영체제", "프로세스", ("유닉스", "리눅스", "chmod", "ls", "pwd", "cd")),
        ]
        for subject, category, primary, keywords in rules:
            if any(keyword.lower() in lowered for keyword in keywords):
                secondary = self._normalize_secondary(category, self.concept_dictionary.detect(body, category=category), primary)
                return self._classification(subject, category, primary, secondary, self._guess_question_type(body), self._normalize_language("", body), body)

        subject = self._guess_category(body)
        question_type = self._guess_question_type(body)
        language = self._normalize_language("", body)
        category = self._guess_analysis_category(body, subject, language)
        primary, secondary = self.concept_dictionary.primary_secondary(body, category=category, language=language)
        if primary == "미분류" or category == "미분류":
            return None
        subject = self.validator.subject_for_category(category)
        if subject == "미분류":
            return None
        secondary = self._normalize_secondary(category, secondary, primary)
        return self._classification(subject, category, primary, secondary, question_type, language, body)

    def _classification(
        self,
        subject: str,
        category: str,
        primary: str,
        secondary: list[str],
        question_type: str,
        language: str,
        body: str,
    ) -> dict[str, Any]:
        """분류 결과 딕셔너리를 생성합니다."""
        concepts = self._ordered_unique([primary, *secondary, *self._guess_keywords(body)])
        mistakes = self._guess_mistakes(body, primary)
        return {
            "subject": subject,
            "category": category,
            "subcategory": primary,
            "sub_category": primary,
            "primary": primary,
            "secondary": secondary,
            "question_type": question_type,
            "language": language,
            "difficulty": "",
            "concepts": concepts,
            "keywords": concepts,
            "intent": self._guess_intent(body, primary, question_type),
            "mistakes": mistakes,
            "wrong_points": ", ".join(mistakes),
        }

    def _unclassified_result(self, question_type: str = "개념 서술", language: str = "") -> dict[str, Any]:
        """임의 기본값 없이 완전 미분류 결과를 반환합니다."""
        return {
            **UNCLASSIFIED,
            "question_type": question_type,
            "language": language,
            "difficulty": "",
            "concepts": [],
            "keywords": [],
            "intent": [],
            "mistakes": [],
            "wrong_points": "",
        }

    def _as_list(self, value: Any) -> list[str]:
        """LLM 또는 규칙 결과를 문자열 리스트로 정규화합니다."""
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in re.split(r"[,/\n]", value) if item.strip()]
        return []

    def _normalize_secondary(self, category: str, values: list[str], primary: str) -> list[str]:
        """secondary 개념을 Dictionary/Tree 안의 값으로 보정합니다."""
        normalized = []
        for value in values:
            concept = self._coerce_subcategory(category, value)
            if concept != "미분류" and concept != primary:
                normalized.append(concept)
        return self._ordered_unique(normalized)

    def _ordered_unique(self, values: list[str]) -> list[str]:
        """순서를 보존하며 중복과 빈 값을 제거합니다."""
        result = []
        seen = set()
        for value in values:
            item = str(value).strip()
            if not item or item in seen or item == "미분류":
                continue
            seen.add(item)
            result.append(item)
        return result

    def _guess_analysis_category(self, body: str, subject: str, language: str) -> str:
        """분석 카테고리를 subject보다 좁은 축으로 추정합니다."""
        if language in {"C", "Java", "Python", "SQL"}:
            return language
        if subject == "SQL 응용":
            return "SQL"
        if "운영체제" in body or "스케줄링" in body or "프로세스" in body:
            return "운영체제"
        if any(keyword in body for keyword in ("TCP", "IP", "OSI", "네트워크", "프로토콜")):
            return "네트워크"
        if any(keyword in body for keyword in ("보안", "공격", "암호", "취약점", "AES", "RSA")):
            return "보안"
        if any(keyword in body for keyword in ("정규화", "ERD", "데이터베이스", "DB", "트랜잭션")):
            return "DB"
        if any(keyword in body for keyword in ("응집도", "결합도", "SOLID", "설계원칙")):
            return "소프트웨어설계"
        if "UML" in body:
            return "UML"
        if "디자인 패턴" in body or "패턴" in body:
            return "디자인패턴"
        if any(keyword in body for keyword in ("테스트", "커버리지", "스텁", "드라이버")):
            return "테스트"
        if any(keyword in body for keyword in ("정렬", "탐색", "알고리즘", "재귀")):
            return "알고리즘"
        if any(keyword in body for keyword in ("스택", "큐", "트리", "그래프", "해시")):
            return "자료구조"
        if "인터페이스" in body:
            return "인터페이스"
        if any(keyword in body for keyword in ("프로젝트", "일정", "위험", "형상관리")):
            return "프로젝트관리"
        if any(keyword in body for keyword in ("신기술", "클라우드", "IoT", "빅데이터", "AI")):
            return "신기술"
        return "미분류"

    def _normalize_analysis_category(self, category: str, body: str, subject: str, language: str) -> str:
        """분석 카테고리를 허용 후보 중 하나로 보정합니다."""
        normalized = category.strip()
        aliases = {
            "데이터베이스": "DB",
            "Database": "DB",
            "보안 공격기법": "보안",
            "디자인 패턴": "디자인패턴",
            "프로그램언어": language if language in {"C", "Java", "Python"} else "C",
            "프로그래밍 언어 활용": language if language in {"C", "Java", "Python"} else "알고리즘",
            "SQL 응용": "SQL",
            "응용 SW 기초 기술 활용": "운영체제",
            "소프트웨어 개발 보안 구축": "보안",
            "애플리케이션 테스트 관리": "테스트",
            "데이터 입출력 구현": "DB",
            "화면 설계": "UML",
            "소프트웨어 설계": "소프트웨어설계",
        }
        normalized = aliases.get(normalized, normalized)
        if normalized in self.ANALYSIS_CATEGORIES and normalized != "미분류":
            return normalized
        return self._guess_analysis_category(body, subject, language)

    def _normalize_category(self, category: str, body: str) -> str:
        """과목을 허용 목록 중 하나로 보정합니다."""
        return category if category in self.CATEGORIES else self._guess_category(body)

    def _normalize_question_type(self, question_type: str, body: str) -> str:
        """문제 유형을 허용 목록 중 하나로 보정합니다."""
        return question_type if question_type in self.QUESTION_TYPES else self._guess_question_type(body)

    def _normalize_language(self, language: str, body: str) -> str:
        """과년도 분석 대상 언어만 반환합니다."""
        lowered_body = body.lower()
        if any(keyword in lowered_body for keyword in self.NON_EXAM_LANGUAGE_KEYWORDS):
            return "기타"

        aliases = {
            "c": "C",
            "c언어": "C",
            "java": "Java",
            "자바": "Java",
            "python": "Python",
            "파이썬": "Python",
            "sql": "SQL",
        }
        lowered_language = language.strip().lower()
        if lowered_language in aliases:
            return aliases[lowered_language]

        detected = detect_language_in_query(body)
        if detected in {"C", "Java", "Python"}:
            return detected
        if detected == "SQL" or self._looks_like_sql(body):
            return "SQL"
        if self._looks_like_c(body):
            return "C"
        if self._looks_like_java(body):
            return "Java"
        if self._looks_like_python(body):
            return "Python"
        if detected:
            return "기타"
        return ""

    def _normalize_sub_category(
        self,
        sub_category: str,
        body: str,
        category: str,
        question_type: str,
        language: str,
    ) -> str:
        """세부 유형을 과목/문제 유형이 아닌 구체 항목으로 보정합니다."""
        blocked = self.CATEGORIES | self.QUESTION_TYPES | self.ANALYSIS_CATEGORIES | self.GENERIC_SUBCATEGORIES
        if any(keyword in sub_category.lower() for keyword in self.NON_EXAM_LANGUAGE_KEYWORDS):
            return self._guess_sub_category(body, category, question_type, language)
        if sub_category and sub_category not in blocked:
            normalized = self._coerce_subcategory(category, sub_category)
            if normalized != "미분류":
                return normalized
        return self._coerce_subcategory(category, self._guess_sub_category(body, category, question_type, language))

    def _coerce_subcategory(self, category: str, subcategory: str) -> str:
        """세부 유형을 정의된 Tree의 항목으로 강제합니다."""
        value = subcategory.strip()
        if not value:
            return "미분류"
        aliases = {
            "C 포인터": "포인터",
            "C 배열": "배열",
            "C 문자열": "문자열",
            "C 함수": "함수",
            "C 재귀": "재귀",
            "C 구조체": "구조체",
            "C 반복문": "증감연산",
            "OSI 7계층": "OSI",
            "3-Way Handshake": "3-way Handshake",
            "Java 클래스": "클래스",
            "Java 상속": "상속",
            "Java 오버라이딩": "오버라이딩",
            "Java 인터페이스": "인터페이스",
            "Java 추상클래스": "추상클래스",
            "Java 컬렉션": "컬렉션",
            "Python 리스트": "리스트",
            "Python 슬라이싱": "슬라이싱",
            "Python 딕셔너리": "딕셔너리",
            "Python 튜플": "튜플",
            "Python set": "Set",
            "Python class": "Class",
            "Python 람다": "Lambda",
            "SQL JOIN": "JOIN",
            "SQL GROUP BY": "GROUP BY",
            "SQL SELECT": "SELECT",
            "SQL 제약조건": "제약조건",
            "UML 관계": "관계",
            "클래스 다이어그램": "Class Diagram",
            "시퀀스 다이어그램": "Sequence Diagram",
            "유스케이스": "UseCase",
            "디자인 패턴": "Singleton",
            "암호화": "AES",
            "보안 공격기법": "SQL Injection",
        }
        value = aliases.get(value, value)
        return value if value in self.CATEGORY_SUBCATEGORIES.get(category, set()) else "미분류"

    def _guess_category(self, body: str) -> str:
        """문제 본문 키워드로 과목을 추정합니다."""
        lowered = body.lower()
        if self._looks_like_c(body) or self._looks_like_java(body) or self._looks_like_python(body):
            return "프로그래밍 언어 활용"
        if self._looks_like_sql(body):
            return "SQL 응용"
        if any(keyword in lowered for keyword in ("int ", "class ", "public", "def ", "포인터", "배열", "리스트", "슬라이싱")):
            return "프로그래밍 언어 활용"
        if any(keyword in body for keyword in ("UML", "유스케이스", "클래스 다이어그램", "시퀀스 다이어그램")):
            return "화면 설계"
        if any(keyword in body for keyword in ("정규화", "데이터베이스 설계", "DB 설계", "외래키", "트랜잭션")):
            return "데이터 입출력 구현"
        if any(keyword in body for keyword in ("응집도", "결합도", "SOLID", "설계원칙")):
            return "서버 프로그램 구현"
        if any(keyword in body for keyword in ("테스트", "커버리지", "스텁", "드라이버")):
            return "애플리케이션 테스트 관리"
        if any(keyword in body for keyword in ("디자인 패턴", "패턴")):
            return "서버 프로그램 구현"
        if any(keyword in body for keyword in ("공격", "보안", "암호", "취약점")):
            return "소프트웨어 개발 보안 구축"
        if any(keyword in body for keyword in ("TCP", "IP", "OSI", "프로토콜", "운영체제", "스케줄링", "네트워크")):
            return "응용 SW 기초 기술 활용"
        return "응용 SW 기초 기술 활용"

    def _guess_sub_category(self, body: str, category: str, question_type: str, language: str) -> str:
        """문제 본문 키워드로 세부 유형을 추정합니다."""
        lowered = body.lower()
        if language == "C":
            if "포인터" in body or "*" in body:
                return "포인터"
            if "구조체" in body or "struct" in lowered:
                return "구조체"
            if "문자열" in body or "char" in lowered:
                return "문자열"
            if "재귀" in body:
                return "재귀"
            if any(keyword in body for keyword in ("반복문", "for", "while")):
                return "증감연산" if "++" in body or "--" in body else "반복문"
            if "배열" in body or "arr" in lowered:
                return "배열"
            return "미분류"
        if language == "Java":
            if "오버라이딩" in body or "override" in lowered:
                return "오버라이딩"
            if "인터페이스" in body or "interface" in lowered:
                return "인터페이스"
            if "추상" in body or "abstract" in lowered:
                return "추상클래스"
            if "생성자" in body:
                return "클래스"
            if "상속" in body or "extends" in lowered:
                return "상속"
            if "컬렉션" in body or "arraylist" in lowered or "hashmap" in lowered:
                return "컬렉션"
            if "클래스" in body or "class " in lowered:
                return "클래스"
            return "미분류"
        if language == "Python":
            if "슬라이싱" in body or "[" in body and ":" in body:
                return "슬라이싱"
            if "딕셔너리" in body or "dict" in lowered:
                return "딕셔너리"
            if "튜플" in body or "tuple" in lowered:
                return "튜플"
            if "set" in lowered or "집합" in body:
                return "Set"
            if "class " in lowered or "클래스" in body:
                return "Class"
            if "리스트" in body or "list" in lowered or "lst" in lowered:
                return "리스트"
            if "lambda" in lowered or "람다" in body:
                return "Lambda"
            return "미분류"
        if language == "SQL":
            if "join" in lowered:
                return "JOIN"
            if "group by" in lowered:
                return "GROUP BY"
            if "having" in lowered:
                return "HAVING"
            if "subquery" in lowered or "서브쿼리" in body:
                return "SUBQUERY"
            if any(keyword in lowered for keyword in ("create", "alter", "drop")):
                return "DDL"
            if any(keyword in lowered for keyword in ("insert", "update", "delete")):
                return "DML"
            if any(keyword in lowered for keyword in ("grant", "revoke")):
                return "DCL"
            if "view" in lowered or "뷰" in body:
                return "VIEW"
            if "foreign key" in lowered or "외래키" in body:
                return "제약조건"
            return "미분류"
        if "포인터" in body:
            return "포인터"
        if "상속" in body:
            return "상속"
        if "오버라이딩" in body:
            return "오버라이딩"
        if "슬라이싱" in body:
            return "슬라이싱"
        if "정규화" in body:
            return "정규화"
        if "디자인 패턴" in body or "패턴" in body:
            return "Singleton"
        if "UML" in body:
            return "관계"
        if "TCP" in body or "IP" in body:
            return "TCP/IP"
        if "OSI" in body:
            return "OSI 7계층"
        if "암호" in body:
            return "AES"
        if "커버리지" in body:
            return "테스트 커버리지"
        if "프로세스" in body:
            return "프로세스"
        if "스레드" in body:
            return "스레드"
        if "교착" in body or "deadlock" in lowered:
            return "교착상태"
        if "스케줄링" in body:
            return "스케줄링"
        if category == "소프트웨어 개발 보안 구축" or category == "보안":
            return "SQL Injection"
        if category == "응용 SW 기초 기술 활용" or category == "운영체제":
            return "프로세스" if question_type == "운영체제" else "미분류"
        if category == "네트워크":
            return "미분류"
        if category == "DB":
            return "정규화"
        if category == "테스트":
            return "테스트 커버리지"
        if category == "자료구조":
            return "스택"
        if category == "알고리즘":
            return "정렬"
        return "미분류"

    def _guess_question_type(self, body: str) -> str:
        """문제 본문 키워드로 문제 유형을 추정합니다."""
        lowered = body.lower()
        if self._looks_like_sql(body):
            if "select" in lowered or "출력" in body or "결과" in body:
                return "SQL 결과"
            if "작성" in body or "쿼리" in body:
                return "SQL 작성"
            return "SQL 결과"
        if any(keyword in lowered for keyword in ("출력", "실행 결과", "print", "printf", "system.out")):
            return "코드 출력"
        if "빈칸" in body or "괄호" in body:
            return "빈칸"
        if "UML" in body:
            return "UML"
        if any(keyword in body for keyword in ("계산", "값을 구", "수를 쓰시오")):
            return "계산"
        if any(keyword in body for keyword in ("공격", "취약점", "보안 공격")):
            return "보안 공격기법"
        if any(keyword in body for keyword in ("TCP", "IP", "OSI", "네트워크", "프로토콜")):
            return "네트워크"
        if any(keyword in body for keyword in ("운영체제", "스케줄링", "프로세스", "메모리")):
            return "운영체제"
        if any(keyword in body for keyword in ("약자", "용어", "명칭")):
            return "용어"
        return "개념 서술"

    def _guess_keywords(self, body: str) -> list[str]:
        """문제 본문에서 대표 키워드를 추정합니다."""
        lowered = body.lower()
        checks = [
            ("포인터", lambda: "포인터" in body),
            ("반복문", lambda: "반복문" in body or "for " in lowered or "while " in lowered),
            ("배열", lambda: "배열" in body),
            ("상속", lambda: "상속" in body or "extends" in lowered),
            ("오버라이딩", lambda: "오버라이딩" in body or "override" in lowered),
            ("리스트", lambda: "리스트" in body or "list" in lowered),
            ("슬라이싱", lambda: "슬라이싱" in body or "[::" in body or "[:" in body),
            ("JOIN", lambda: re.search(r"(?<!\.)\bjoin\b", lowered) is not None),
            ("GROUP BY", lambda: re.search(r"\bgroup\s+by\b", lowered) is not None),
            ("HAVING", lambda: re.search(r"\bhaving\b", lowered) is not None),
            ("정규화", lambda: "정규화" in body),
            ("UML", lambda: "UML" in body),
            ("디자인 패턴", lambda: "디자인 패턴" in body or "패턴" in body),
            ("TCP/IP", lambda: "TCP" in body or "IP" in body),
            ("OSI", lambda: "OSI" in body),
            ("암호화", lambda: "암호" in body),
            ("커버리지", lambda: "커버리지" in body),
            ("보안", lambda: "보안" in body),
            ("네트워크", lambda: "네트워크" in body),
        ]
        return [keyword for keyword, predicate in checks if predicate()][:5]

    def _guess_intent(self, body: str, subcategory: str, question_type: str) -> list[str]:
        """문제 출제 목적을 규칙 기반으로 추정합니다."""
        if subcategory == "포인터":
            return ["포인터 증가 이해", "배열 주소 계산"]
        if subcategory in self.CATEGORY_SUBCATEGORIES["Java"]:
            return ["객체지향 문법 이해", subcategory + " 이해"]
        if subcategory in self.CATEGORY_SUBCATEGORIES["Python"]:
            return ["Python 자료구조 이해", subcategory + " 이해"]
        if subcategory in {"JOIN", "GROUP BY", "HAVING", "SUBQUERY", "SELECT", "DDL", "DML", "DCL", "제약조건", "VIEW"}:
            return [subcategory + " 이해", "SQL 실행 결과 해석"]
        if question_type == "보안 공격기법":
            return ["공격 기법 특징 구분"]
        if question_type == "네트워크":
            return ["네트워크 계층/프로토콜 이해"]
        return [f"{subcategory} 핵심 개념 이해"] if subcategory else ["핵심 개념 이해"]

    def _guess_mistakes(self, body: str, subcategory: str) -> list[str]:
        """시험장에서 자주 틀리는 포인트를 규칙 기반으로 추정합니다."""
        if subcategory == "포인터":
            return ["*p++", "(*p)++", "주소 증가와 값 증가 혼동"]
        if subcategory == "증감연산":
            return ["break 위치", "continue 위치", "증감식 실행 순서"]
        if subcategory in self.CATEGORY_SUBCATEGORIES["Java"]:
            return ["오버라이딩 대상 메서드", "동적 바인딩", "상속 호출 순서"]
        if subcategory == "슬라이싱":
            return ["슬라이싱 끝 인덱스", "역순 슬라이싱", "문자열 join 결과"]
        if subcategory in {"JOIN", "GROUP BY", "HAVING", "SUBQUERY", "SELECT", "DDL", "DML", "DCL", "제약조건", "VIEW"}:
            return ["JOIN 조건", "GROUP BY 기준", "NULL 처리", "집계 함수 적용 순서"]
        if "보안" in subcategory:
            return ["공격 절차와 명칭 혼동"]
        return []

    def _looks_like_sql(self, body: str) -> bool:
        """SQL 문제인지 추정합니다."""
        lowered = body.lower()
        return any(
            re.search(pattern, lowered)
            for pattern in (
                r"\bsql\b",
                r"\bselect\b",
                r"(?<!\.)\bjoin\b",
                r"\bgroup\s+by\b",
                r"\bhaving\b",
                r"\binsert\b",
                r"\bupdate\b",
                r"\bdelete\b",
                r"\bforeign\s+key\b",
            )
        ) or any(keyword in body for keyword in ("외래키", "테이블", "행(Row)"))

    def _looks_like_c(self, body: str) -> bool:
        """C 코드 문제인지 추정합니다."""
        lowered = body.lower()
        return "#include" in lowered or "printf" in lowered or bool(re.search(r"\bint\s+main\s*\(", lowered))

    def _looks_like_java(self, body: str) -> bool:
        """Java 코드 문제인지 추정합니다."""
        lowered = body.lower()
        return "system.out" in lowered or "public static void main" in lowered or "class " in lowered and ";" in lowered

    def _looks_like_python(self, body: str) -> bool:
        """Python 코드 문제인지 추정합니다."""
        lowered = body.lower()
        return "print(" in lowered or "def " in lowered or "range(" in lowered or "input(" in lowered
