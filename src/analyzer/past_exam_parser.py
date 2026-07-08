"""과년도 기출문제 텍스트를 문제 단위로 분리합니다."""

from __future__ import annotations

import re

from src.models import PastExamQuestion


class PastExamParser:
    """기출문제 텍스트에서 문제 번호, 본문, 정답, 해설을 추출합니다."""

    _MARKDOWN_HEADING_QUESTION_PATTERN = re.compile(
        r"(?m)^\s*#{1,6}\s*(?:\[?\s*문제\s*)?(\d{1,2})(?:\s*번)?(?:\s*\]|\s*[.)]|\s+)",
        re.IGNORECASE,
    )
    _QUESTION_PATTERN = re.compile(
        r"(?m)^\s*(?:\[?\s*문제\s*)?(\d{1,2})(?:\s*\]|\s*[.)]|(?:\s+))|^\s*Q\s*(\d{1,2})\b",
        re.IGNORECASE,
    )
    _ANSWER_PATTERN = re.compile(r"(?im)^\s*(정답|답|answer)\s*[:：]?\s*")
    _EXPLANATION_PATTERN = re.compile(r"(?im)^\s*(해설|풀이|설명|explanation)\s*[:：]?\s*")

    def parse_questions(self, text: str) -> list[PastExamQuestion]:
        """텍스트를 문제 단위로 분리합니다."""
        matches = self._question_matches(text)
        if not matches:
            cleaned = text.strip()
            return [PastExamQuestion(question_number=1, body=cleaned)] if cleaned else []

        questions: list[PastExamQuestion] = []
        for index, match in enumerate(matches):
            number_text = match.group(1) or match.group(2)
            number = int(number_text)
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            block = text[start:end].strip()
            body, answer, explanation = self._split_answer_and_explanation(block)
            if body:
                questions.append(
                    PastExamQuestion(
                        question_number=number,
                        body=body,
                        answer=answer,
                        explanation=explanation,
                    )
                )
        return questions

    def has_question_markers(self, text: str) -> bool:
        """문제 번호 패턴이 텍스트에 존재하는지 확인합니다."""
        return bool(self._question_matches(text))

    def _question_matches(self, text: str) -> list[re.Match[str]]:
        """Markdown 문제 제목을 우선하고, 없을 때 일반 번호 패턴을 사용합니다."""
        markdown_matches = list(self._MARKDOWN_HEADING_QUESTION_PATTERN.finditer(text))
        if markdown_matches:
            return markdown_matches
        return list(self._QUESTION_PATTERN.finditer(text))

    def _split_answer_and_explanation(self, block: str) -> tuple[str, str, str]:
        """문제 블록에서 정답과 해설 영역을 분리합니다."""
        answer = ""
        explanation = ""
        body = block.strip()

        explanation_match = self._EXPLANATION_PATTERN.search(body)
        if explanation_match:
            explanation = body[explanation_match.end() :].strip()
            body = body[: explanation_match.start()].strip()

        answer_match = self._ANSWER_PATTERN.search(body)
        if answer_match:
            answer = body[answer_match.end() :].strip()
            body = body[: answer_match.start()].strip()

        return body, answer, explanation
