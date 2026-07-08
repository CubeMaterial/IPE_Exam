"""과년도 기출 분석 기능을 검증합니다."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from src.analyzer.frequency_analyzer import FrequencyAnalyzer
from src.analyzer.coverage_analyzer import CoverageAnalyzer
from src.analyzer.concept_dictionary import ConceptDictionary
from src.analyzer.cycle_analyzer import CycleAnalyzer
from src.analyzer.exam_tree import ExamTreeBuilder
from src.analyzer.flow_analyzer import FlowAnalyzer
from src.analyzer.gap_analyzer import GapAnalyzer
from src.analyzer.past_exam_classifier import PastExamClassifier
from src.analyzer.past_exam_indexer import PastExamIndexer
from src.analyzer.past_exam_parser import PastExamParser
from src.analyzer.post_validation import ClassificationValidator
from src.analyzer.study_coach import StudyCoach
from src.analyzer.stability_analyzer import StabilityAnalyzer
from src.analyzer.topic_cluster import TopicClusterAnalyzer
from src.analyzer.prediction_analyzer import PredictionAnalyzer
from src.analyzer.unclassified_reporter import UnclassifiedReporter
from src.models import PastExamQuestion


class PastExamParserTest(TestCase):
    """기출문제 파서 테스트입니다."""

    def test_parse_numbered_questions_with_answer(self) -> None:
        """문제 번호와 정답 영역을 분리합니다."""
        text = """
1. C 포인터 출력 결과는?
정답: 3

[문제 2] SQL JOIN 설명으로 옳은 것은?
해설: INNER JOIN은 교집합이다.
"""

        questions = PastExamParser().parse_questions(text)

        self.assertEqual(len(questions), 2)
        self.assertEqual(questions[0].question_number, 1)
        self.assertIn("C 포인터", questions[0].body)
        self.assertEqual(questions[0].answer, "3")
        self.assertEqual(questions[1].question_number, 2)
        self.assertIn("INNER JOIN", questions[1].explanation)
        self.assertTrue(PastExamParser().has_question_markers(text))

    def test_parse_markdown_heading_questions(self) -> None:
        """Markdown 제목 형식의 문제 번호를 우선 분리합니다."""
        text = """
# 2026년 1회 정보처리기사 실기 복원 문제

## 1번. C언어 출력값

다음 코드의 출력 결과를 쓰시오.

## 2번. 디자인 패턴

다음 설명에 해당하는 디자인 패턴을 쓰시오.
1. 보기 번호는 문제 번호로 분리하면 안 된다.
2. 보기 번호도 같은 문제 본문에 남아야 한다.
"""

        questions = PastExamParser().parse_questions(text)

        self.assertEqual(len(questions), 2)
        self.assertEqual(questions[0].question_number, 1)
        self.assertIn("C언어 출력값", questions[0].body)
        self.assertEqual(questions[1].question_number, 2)
        self.assertIn("보기 번호도 같은 문제 본문", questions[1].body)
        self.assertTrue(PastExamParser().has_question_markers(text))


class FrequencyAnalyzerTest(TestCase):
    """기출 빈도 분석 테스트입니다."""

    def test_analyze_counts_category_and_language(self) -> None:
        """세부 유형과 언어별 빈도를 계산합니다."""
        records = [
            {"year": 2024, "round": 1, "category": "프로그래밍 언어 활용", "sub_category": "C 포인터", "question_type": "코드 출력", "language": "C"},
            {"year": 2025, "round": 2, "category": "프로그래밍 언어 활용", "sub_category": "C 포인터", "question_type": "코드 출력", "language": "C"},
            {"year": 2025, "round": 3, "category": "SQL 응용", "sub_category": "SQL JOIN", "question_type": "SQL 결과", "language": "SQL"},
        ]

        analysis = FrequencyAnalyzer().analyze(records)

        self.assertEqual(analysis["sub_category"]["C 포인터"], 2)
        self.assertEqual(analysis["language"]["C"], 2)
        self.assertEqual(analysis["question_type"]["코드 출력"], 2)

    def test_analyze_combines_recent_years_and_category_filter(self) -> None:
        """최근 3개년과 특정 과목 필터를 동시에 적용합니다."""
        records = [
            {"year": 2022, "round": 1, "category": "프로그래밍 언어 활용", "sub_category": "C 포인터", "question_type": "코드 출력", "language": "C"},
            {"year": 2023, "round": 1, "category": "SQL 응용", "sub_category": "SQL JOIN", "question_type": "SQL 결과", "language": "SQL"},
            {"year": 2024, "round": 1, "category": "프로그래밍 언어 활용", "sub_category": "Python 코드", "question_type": "코드 출력", "language": "Python"},
            {"year": 2025, "round": 1, "category": "프로그래밍 언어 활용", "sub_category": "Java 코드", "question_type": "코드 출력", "language": "Java"},
        ]

        analysis = FrequencyAnalyzer().analyze(records, basis="최근 3개년", category="프로그래밍 언어 활용")

        self.assertEqual(analysis["total_count"], 2)
        self.assertEqual(analysis["language"]["Python"], 1)
        self.assertEqual(analysis["language"]["Java"], 1)
        self.assertNotIn("C", analysis["language"])


class PastExamIndexerIdentityTest(TestCase):
    """기출 파일명/본문에서 연도와 회차를 추출하는 기능을 검증합니다."""

    def test_extract_exam_identity_from_filename(self) -> None:
        """파일명에 있는 연도와 회차를 우선 사용합니다."""
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "2026_1회_정보처리기사_실기_복원문제.md"
            path.write_text("# 본문", encoding="utf-8")

            self.assertEqual(PastExamIndexer().extract_exam_identity(path), (2026, 1))

    def test_extract_exam_identity_from_markdown_body(self) -> None:
        """파일명에 없으면 Markdown 본문에서 연도와 회차를 찾습니다."""
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "past_exam.md"
            path.write_text("# 2025년 3회 정보처리기사 실기 복원 문제", encoding="utf-8")

            self.assertEqual(PastExamIndexer().extract_exam_identity(path), (2025, 3))

    def test_reset_past_exam_data_removes_files_and_vectors(self) -> None:
        """과년도 기출 파일, JSON 인덱스, 벡터 Chunk를 초기화합니다."""
        from config.config import CONFIG

        class FakeStore:
            def __init__(self) -> None:
                self.filter = None

            def delete_by_filter(self, metadata_filter):
                self.filter = metadata_filter
                return 7

        with TemporaryDirectory() as temp_dir:
            original_past_exam_dir = CONFIG.past_exam_dir
            original_index_dir = CONFIG.past_exam_index_dir
            original_index_file = CONFIG.past_exam_index_file
            temp_path = Path(temp_dir)
            CONFIG.past_exam_dir = temp_path / "past_exams"
            CONFIG.past_exam_index_dir = CONFIG.past_exam_dir / "index"
            CONFIG.past_exam_index_file = CONFIG.past_exam_index_dir / "past_exam_index.json"
            try:
                copied_file = CONFIG.past_exam_dir / "2026" / "round_1" / "sample.md"
                copied_file.parent.mkdir(parents=True)
                copied_file.write_text("sample", encoding="utf-8")
                CONFIG.past_exam_index_dir.mkdir(parents=True)
                CONFIG.past_exam_index_file.write_text("[]", encoding="utf-8")
                store = FakeStore()

                report = PastExamIndexer(store=store).reset_past_exam_data()

                self.assertEqual(store.filter, {"source_type": "past_exam"})
                self.assertEqual(report.deleted_vector_chunks, 7)
                self.assertTrue(CONFIG.past_exam_dir.exists())
                self.assertTrue(CONFIG.past_exam_index_dir.exists())
                self.assertFalse(copied_file.exists())
                self.assertFalse(CONFIG.past_exam_index_file.exists())
            finally:
                CONFIG.past_exam_dir = original_past_exam_dir
                CONFIG.past_exam_index_dir = original_index_dir
                CONFIG.past_exam_index_file = original_index_file

    def test_copy_markdown_assets_with_exam_file(self) -> None:
        """Markdown 기출이 참조하는 assets 이미지를 함께 복사합니다."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_dir = root / "source"
            source_dir.mkdir()
            assets = source_dir / "assets"
            assets.mkdir()
            image = assets / "part1.png"
            image.write_bytes(b"image")
            markdown = source_dir / "2025년_1회_기출.md"
            markdown.write_text("![[part](assets/part1.png)]", encoding="utf-8")
            target_dir = root / "target"
            target_dir.mkdir()

            copied = PastExamIndexer()._copy_to_exam_dir(markdown, target_dir)

            self.assertTrue(copied.exists())
            self.assertTrue((target_dir / "assets" / "part1.png").exists())


class PastExamClassifierRuleTest(TestCase):
    """정보처리기사 실기 기출 분류 규칙을 검증합니다."""

    def test_non_exam_code_language_is_other(self) -> None:
        """TypeScript 등 비대상 언어는 기타로 분류합니다."""
        question = PastExamQuestion(
            question_number=1,
            body="""
다음 TypeScript 코드의 출력 결과를 쓰시오.
class User {
  name: string;
}
console.log('ok');
""",
        )

        result = PastExamClassifier(use_llm=False).classify(question)

        self.assertEqual(result["subject"], "미분류")
        self.assertEqual(result["category"], "미분류")
        self.assertEqual(result["subcategory"], "미분류")
        self.assertEqual(result["question_type"], "코드 출력")

    def test_sql_is_not_mixed_with_sub_category(self) -> None:
        """SQL 과목, 문제 유형, 세부 유형을 분리합니다."""
        question = PastExamQuestion(
            question_number=2,
            body="다음 SQL SELECT문에서 GROUP BY와 HAVING을 적용한 결과를 쓰시오.",
        )

        result = PastExamClassifier(use_llm=False).classify(question)

        self.assertEqual(result["subject"], "SQL 응용")
        self.assertEqual(result["category"], "SQL")
        self.assertEqual(result["question_type"], "SQL 결과")
        self.assertEqual(result["subcategory"], "GROUP BY")
        self.assertEqual(result["language"], "SQL")

    def test_classifier_outputs_allowed_category_and_question_type(self) -> None:
        """과목과 문제 유형은 허용 목록 안에서만 반환합니다."""
        question = PastExamQuestion(
            question_number=3,
            body="다음 설명에 해당하는 디자인 패턴의 명칭을 쓰시오.",
        )

        result = PastExamClassifier(use_llm=False).classify(question)

        self.assertEqual(result["subject"], "미분류")
        self.assertIn(result["question_type"], PastExamClassifier.QUESTION_TYPES)
        self.assertEqual(result["category"], "미분류")
        self.assertEqual(result["subcategory"], "미분류")

    def test_classifier_outputs_primary_and_secondary_from_dictionary(self) -> None:
        """C 코드가 무조건 포인터로 몰리지 않고 primary/secondary를 저장합니다."""
        question = PastExamQuestion(
            question_number=4,
            body="""
다음 C 코드의 출력 결과를 쓰시오.
int arr[3] = {1, 2, 3};
for (int i = 0; i < 3; i++) {
  arr[i]++;
}
""",
        )

        result = PastExamClassifier(use_llm=False).classify(question)

        self.assertEqual(result["category"], "C")
        self.assertEqual(result["primary"], "증감연산")
        self.assertIn("배열", result["secondary"])
        self.assertIn("반복문", result["secondary"])
        self.assertNotEqual(result["primary"], "포인터")


class StudyCoachEngineTest(TestCase):
    """AI 학습 코치용 Python 계산 모듈을 검증합니다."""

    def test_exam_tree_and_flow_use_structured_records(self) -> None:
        """출제 트리와 흐름은 LLM 계산 없이 레코드에서 만들어집니다."""
        records = [
            {"year": 2024, "round": 1, "question_number": 1, "subject": "프로그래밍 언어 활용", "category": "C", "subcategory": "포인터"},
            {"year": 2025, "round": 1, "question_number": 2, "subject": "SQL 응용", "category": "SQL", "subcategory": "JOIN"},
            {"year": 2026, "round": 1, "question_number": 3, "subject": "프로그래밍 언어 활용", "category": "C", "subcategory": "포인터"},
        ]

        tree = ExamTreeBuilder().build(records)
        flow = FlowAnalyzer().analyze(records)

        self.assertEqual(tree["프로그래밍 언어 활용"]["categories"]["C"]["subcategories"]["포인터"]["count"], 2)
        self.assertEqual(flow["recent_exam_counts"]["포인터"], 2)
        self.assertEqual(flow["recent_question_counts"]["포인터"], 2)

    def test_study_coach_scores_priorities(self) -> None:
        """학습 코치는 빈도/최근성 기반으로 우선순위를 계산합니다."""
        records = [
            {"year": 2024, "subcategory": "포인터", "concepts": ["포인터", "배열"]},
            {"year": 2025, "subcategory": "포인터", "concepts": ["포인터", "증감연산자"]},
            {"year": 2026, "subcategory": "JOIN", "concepts": ["JOIN", "GROUP BY"]},
        ]

        priorities = StudyCoach().priorities(records)

        self.assertEqual(priorities[0]["subcategory"], "포인터")
        self.assertIn("★", priorities[0]["stars"])

    def test_gap_cycle_and_coverage_are_python_calculated(self) -> None:
        """공백, 주기, 커버리지는 Python에서 계산됩니다."""
        records = [
            {"year": 2024, "round": 1, "question_number": 1, "subject": "프로그래밍 언어 활용", "category": "C", "subcategory": "포인터"},
            {"year": 2024, "round": 2, "question_number": 1, "subject": "SQL 응용", "category": "SQL", "subcategory": "JOIN"},
            {"year": 2025, "round": 1, "question_number": 1, "subject": "프로그래밍 언어 활용", "category": "C", "subcategory": "배열"},
            {"year": 2026, "round": 1, "question_number": 1, "subject": "프로그래밍 언어 활용", "category": "C", "subcategory": "포인터"},
        ]

        gap = GapAnalyzer().analyze(records)
        cycle = CycleAnalyzer().analyze(records)
        tree = ExamTreeBuilder().build(records)
        coverage = CoverageAnalyzer().analyze(tree, {"포인터", "JOIN"})

        self.assertEqual(gap["gaps"]["JOIN"]["gap"], 2)
        self.assertEqual(cycle["cycles"]["포인터"]["average_cycle"], 3)
        self.assertEqual(coverage["completed"], 2)

    def test_unclassified_is_excluded_from_strategy_targets(self) -> None:
        """미분류는 흐름/공백/주기/우선순위 대상에서 제외하고 별도 보고합니다."""
        records = [
            {"year": 2026, "round": 1, "question_number": 1, "subject": "프로그래밍 언어 활용", "category": "C", "subcategory": "포인터", "body": "포인터 문제"},
            {"year": 2026, "round": 1, "question_number": 2, "subject": "응용 SW 기초 기술 활용", "category": "미분류", "subcategory": "미분류", "body": "분류 어려운 문제"},
        ]

        flow = FlowAnalyzer().analyze(records)
        gap = GapAnalyzer().analyze(records)
        cycle = CycleAnalyzer().analyze(records)
        priorities = StudyCoach().priorities(records)
        unclassified = UnclassifiedReporter().collect(records)

        self.assertNotIn("미분류", flow["subcategory_timeline"])
        self.assertNotIn("미분류", gap["gaps"])
        self.assertNotIn("미분류", cycle["cycles"])
        self.assertNotIn("미분류", [item["subcategory"] for item in priorities])
        self.assertEqual(len(unclassified), 1)

    def test_invalid_taxonomy_combination_is_reset_and_recorded(self) -> None:
        """잘못된 subject/category/subcategory 조합은 미분류 처리하고 기록합니다."""
        with TemporaryDirectory() as temp_dir:
            invalid_path = Path(temp_dir) / "invalid_classifications.json"
            validator = ClassificationValidator(invalid_path=invalid_path)

            result = validator.validate_classification(
                {
                    "subject": "SQL 응용",
                    "category": "SQL",
                    "subcategory": "증감연산",
                    "primary": "증감연산",
                    "secondary": ["배열"],
                }
            )

            self.assertEqual(result["category"], "미분류")
            self.assertEqual(result["subcategory"], "미분류")
            self.assertEqual(result["primary"], "미분류")
            self.assertEqual(result["secondary"], [])
            self.assertTrue(invalid_path.exists())

    def test_fallback_does_not_assign_forbidden_defaults_to_unknown(self) -> None:
        """분류 실패 시 금지 기본값을 임의로 넣지 않습니다."""
        question = PastExamQuestion(question_number=5, body="다음 설명에 해당하는 용어를 쓰시오. 전혀 단서가 없다.")

        result = PastExamClassifier(use_llm=False).classify(question)

        self.assertEqual(result["subject"], "미분류")
        self.assertEqual(result["category"], "미분류")
        self.assertEqual(result["subcategory"], "미분류")
        self.assertEqual(result["primary"], "미분류")
        self.assertEqual(result["secondary"], [])

    def test_stability_cluster_and_prediction_are_python_calculated(self) -> None:
        """안정도, 클러스터, 출제 가능성은 Python에서 계산합니다."""
        records = [
            {"year": 2024, "round": 1, "category": "SQL", "primary": "JOIN", "subcategory": "JOIN", "secondary": ["GROUP BY"], "concepts": ["JOIN", "GROUP BY"]},
            {"year": 2024, "round": 2, "category": "SQL", "primary": "GROUP BY", "subcategory": "GROUP BY", "secondary": ["집계함수"], "concepts": ["GROUP BY", "집계함수"]},
            {"year": 2025, "round": 1, "category": "SQL", "primary": "JOIN", "subcategory": "JOIN", "secondary": ["HAVING"], "concepts": ["JOIN", "HAVING"]},
        ]
        stability = StabilityAnalyzer().analyze(records)
        clusters = TopicClusterAnalyzer().analyze(records)
        predictions = PredictionAnalyzer().analyze(
            records,
            gap_scores={"JOIN": 0, "GROUP BY": 1},
            stability_scores=StabilityAnalyzer().score_map(stability),
            cluster_scores=TopicClusterAnalyzer().cluster_score_map(clusters),
            recent_change={},
        )

        self.assertEqual(stability["stability"]["JOIN"]["exam_count"], 2)
        self.assertTrue(any("JOIN" in cluster["concepts"] and "GROUP BY" in cluster["concepts"] for cluster in clusters["clusters"]))
        self.assertEqual(predictions[0]["concept"], "JOIN")

    def test_topic_cluster_separates_languages(self) -> None:
        """C, Java, Python 개념은 하나의 거대 클러스터로 합쳐지지 않습니다."""
        records = [
            {"category": "C", "primary": "포인터", "secondary": ["배열"], "concepts": ["포인터", "배열"]},
            {"category": "Java", "primary": "상속", "secondary": ["오버라이딩"], "concepts": ["상속", "오버라이딩"]},
            {"category": "Python", "primary": "리스트", "secondary": ["슬라이싱"], "concepts": ["리스트", "슬라이싱"]},
        ]

        clusters = TopicClusterAnalyzer().analyze(records)["clusters"]
        cluster_map = {cluster["id"]: cluster["concepts"] for cluster in clusters}

        self.assertIn("C 클러스터", cluster_map)
        self.assertIn("Java 클러스터", cluster_map)
        self.assertIn("Python 클러스터", cluster_map)
        self.assertNotIn("상속", cluster_map["C 클러스터"])

    def test_concept_dictionary_detects_multiple_concepts(self) -> None:
        """Concept Dictionary는 한 문제에서 여러 개념을 탐지합니다."""
        primary, secondary = ConceptDictionary().primary_secondary("int arr[3]; arr[0]++;", category="C")

        self.assertEqual(primary, "증감연산")
        self.assertIn("배열", secondary)
