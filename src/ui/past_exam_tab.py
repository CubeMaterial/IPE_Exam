"""과년도 기출 분석 탭을 제공합니다."""

from __future__ import annotations

from pathlib import Path
from datetime import date

from PySide6.QtCore import QDate, Qt, QThread, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QDateEdit,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.analyzer.coverage_analyzer import CoverageAnalyzer
from src.analyzer.cycle_analyzer import CycleAnalyzer
from src.analyzer.exam_tree import ExamTreeBuilder
from src.analyzer.exam_strategy_analyzer import ExamStrategyAnalyzer
from src.analyzer.flow_analyzer import FlowAnalyzer
from src.analyzer.frequency_analyzer import FrequencyAnalyzer
from src.analyzer.gap_analyzer import GapAnalyzer
from src.analyzer.past_exam_indexer import PastExamIndexer, PastExamIndexReport, PastExamResetReport
from src.analyzer.post_validation import ClassificationValidator
from src.analyzer.prediction_analyzer import PredictionAnalyzer
from src.analyzer.relation_analyzer import RelationAnalyzer
from src.analyzer.stability_analyzer import StabilityAnalyzer
from src.analyzer.statistics_engine import StatisticsEngine
from src.analyzer.study_coach import StudyCoach
from src.analyzer.topic_cluster import TopicClusterAnalyzer
from src.analyzer.unclassified_reporter import UnclassifiedReporter
from src.generator.expected_question_generator import ExpectedQuestionGenerator
from src.ui.document_tab import SUPPORTED_FILE_FILTER
from src.ui.worker import Worker


class PastExamTab(QWidget):
    """과년도 기출 등록, 빈도 분석, 전략 생성, 예상문제 생성을 담당합니다."""

    def __init__(self) -> None:
        """과년도 기출 분석 탭 UI를 초기화합니다."""
        super().__init__()
        self.selected_files: list[Path] = []
        self.thread: QThread | None = None
        self.worker: Worker | None = None
        self.worker_output: QTextEdit | None = None
        self.worker_result_handler = None
        self.indexer = PastExamIndexer()
        self._build_ui()

    def _build_ui(self) -> None:
        """탭 화면 구성요소를 생성합니다."""
        layout = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._registration_group())
        splitter.addWidget(self._analysis_group())
        splitter.addWidget(self._coach_group())
        splitter.addWidget(self._strategy_group())
        splitter.addWidget(self._generation_group())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 3)
        splitter.setStretchFactor(3, 2)
        splitter.setStretchFactor(4, 2)
        splitter.setSizes([180, 420, 320, 220, 220])
        content_layout.addWidget(splitter)
        scroll_area.setWidget(content)
        layout.addWidget(scroll_area)

    def _registration_group(self) -> QGroupBox:
        """기출 등록 영역을 생성합니다."""
        group = QGroupBox("기출 등록")
        layout = QVBoxLayout(group)
        controls = QHBoxLayout()
        self.year_combo = QComboBox()
        self.year_combo.addItems([str(year) for year in range(2020, 2027)])
        self.round_combo = QComboBox()
        self.round_combo.addItems(["1회", "2회", "3회"])
        self.file_button = QPushButton("파일 선택")
        self.folder_button = QPushButton("폴더 선택")
        self.register_button = QPushButton("선택 연도/회차로 등록")
        self.auto_register_button = QPushButton("파일명/본문 기준 자동 등록")
        self.reset_button = QPushButton("기출 데이터 초기화")
        self.llm_classify_checkbox = QCheckBox("LLM 분류 사용(느림)")
        self.llm_classify_checkbox.setChecked(False)
        self.file_button.clicked.connect(self._select_files)
        self.folder_button.clicked.connect(self._select_folder)
        self.register_button.clicked.connect(self._register_files)
        self.auto_register_button.clicked.connect(self._register_files_auto)
        self.reset_button.clicked.connect(self._reset_past_exam_data)
        controls.addWidget(self.year_combo)
        controls.addWidget(self.round_combo)
        controls.addWidget(self.file_button)
        controls.addWidget(self.folder_button)
        controls.addWidget(self.register_button)
        controls.addWidget(self.auto_register_button)
        controls.addWidget(self.reset_button)
        controls.addWidget(self.llm_classify_checkbox)
        self.file_list = QListWidget()
        self.register_log = QTextEdit()
        self.register_log.setReadOnly(True)
        layout.addLayout(controls)
        layout.addWidget(self.file_list)
        layout.addWidget(self.register_log)
        return group

    def _coach_group(self) -> QGroupBox:
        """AI 학습 코치 영역을 생성합니다."""
        group = QGroupBox("AI 학습 코치")
        layout = QVBoxLayout(group)
        controls = QGridLayout()
        self.exam_date_input = QDateEdit()
        self.exam_date_input.setCalendarPopup(True)
        self.exam_date_input.setDate(QDate.currentDate().addDays(30))
        self.study_hours_spin = QSpinBox()
        self.study_hours_spin.setRange(1, 12)
        self.study_hours_spin.setValue(3)
        self.tree_button = QPushButton("출제 트리")
        self.flow_button = QPushButton("출제 흐름")
        self.relation_button = QPushButton("연관 개념")
        self.gap_button = QPushButton("출제 공백")
        self.cycle_button = QPushButton("출제 주기")
        self.stability_button = QPushButton("출제 안정도")
        self.cluster_button = QPushButton("Topic Cluster")
        self.prediction_button = QPushButton("출제 가능성")
        self.coverage_button = QPushButton("커버리지 계산")
        self.today_button = QPushButton("오늘 공부 추천")
        self.roadmap_button = QPushButton("학습 로드맵")
        self.wrong_answer_button = QPushButton("오답 분석")
        self.tree_button.clicked.connect(self._run_exam_tree)
        self.flow_button.clicked.connect(self._run_exam_flow)
        self.relation_button.clicked.connect(self._run_relation_graph)
        self.gap_button.clicked.connect(self._run_gap_analysis)
        self.cycle_button.clicked.connect(self._run_cycle_analysis)
        self.stability_button.clicked.connect(self._run_stability_analysis)
        self.cluster_button.clicked.connect(self._run_topic_cluster)
        self.prediction_button.clicked.connect(self._run_prediction_analysis)
        self.coverage_button.clicked.connect(self._run_coverage)
        self.today_button.clicked.connect(self._run_today_study)
        self.roadmap_button.clicked.connect(self._run_roadmap)
        self.wrong_answer_button.clicked.connect(self._run_wrong_answer)
        buttons = [
            self.tree_button,
            self.flow_button,
            self.relation_button,
            self.gap_button,
            self.cycle_button,
            self.stability_button,
            self.cluster_button,
            self.prediction_button,
            self.coverage_button,
            self.today_button,
            self.roadmap_button,
            self.wrong_answer_button,
        ]
        controls.addWidget(self.exam_date_input, 0, 0)
        controls.addWidget(self.study_hours_spin, 0, 1)
        for index, button in enumerate(buttons):
            button.setMinimumWidth(110)
            row = 1 + index // 3
            column = index % 3
            controls.addWidget(button, row, column)
        for column in range(3):
            controls.setColumnStretch(column, 1)
        self.wrong_answer_input = QTextEdit()
        self.wrong_answer_input.setPlaceholderText("오답/완료 키워드 예: 포인터 3회, JOIN 2회, TCP/IP 완료")
        self.coverage_progress = QProgressBar()
        self.coverage_progress.setRange(0, 100)
        self.coverage_progress.setValue(0)
        self.coach_output = QTextEdit()
        self.coach_output.setReadOnly(True)
        self.coach_output.setMinimumHeight(180)
        layout.addLayout(controls)
        layout.addWidget(self.wrong_answer_input)
        layout.addWidget(self.coverage_progress)
        layout.addWidget(self.coach_output)
        return group

    def _analysis_group(self) -> QGroupBox:
        """빈도 분석 영역을 생성합니다."""
        group = QGroupBox("분석")
        layout = QVBoxLayout(group)
        controls = QHBoxLayout()
        self.analysis_period_combo = QComboBox()
        self.analysis_period_combo.addItems(["전체 기간", "최근 3개년", "특정 연도"])
        self.analysis_year_combo = QComboBox()
        self.analysis_year_combo.addItems([str(year) for year in range(2020, 2027)])
        self.analysis_category_combo = QComboBox()
        self.analysis_category_combo.addItems(["전체 과목", "프로그래밍 언어 활용", "SQL 응용", "소프트웨어 개발 보안 구축", "응용 SW 기초 기술 활용"])
        self.analysis_button = QPushButton("분석 실행")
        self.analysis_period_combo.currentTextChanged.connect(self._update_analysis_filters)
        self.analysis_button.clicked.connect(self._run_frequency_analysis)
        controls.addWidget(self.analysis_period_combo)
        controls.addWidget(self.analysis_year_combo)
        controls.addWidget(self.analysis_category_combo)
        controls.addWidget(self.analysis_button)
        self.analysis_output = QTextEdit()
        self.analysis_output.setReadOnly(True)
        self.analysis_output.setMinimumHeight(220)
        layout.addLayout(controls)
        layout.addWidget(self.analysis_output)
        self._update_analysis_filters()
        return group

    def _strategy_group(self) -> QGroupBox:
        """다음 시험 대비 전략 영역을 생성합니다."""
        group = QGroupBox("전략")
        layout = QVBoxLayout(group)
        self.strategy_button = QPushButton("다음 시험 대비 전략 생성")
        self.strategy_button.clicked.connect(self._run_strategy)
        self.strategy_output = QTextEdit()
        self.strategy_output.setReadOnly(True)
        self.strategy_output.setMinimumHeight(140)
        layout.addWidget(self.strategy_button)
        layout.addWidget(self.strategy_output)
        return group

    def _generation_group(self) -> QGroupBox:
        """과년도 기출 기반 예상문제 생성 영역을 생성합니다."""
        group = QGroupBox("예상문제")
        layout = QVBoxLayout(group)
        controls = QHBoxLayout()
        self.topic_input = QTextEdit()
        self.topic_input.setPlaceholderText("예: 2020~2026 기출 기반으로 C 포인터 문제")
        self.question_type_combo = QComboBox()
        self.question_type_combo.addItems(["객관식", "주관식", "코드 출력", "SQL", "OX", "빈칸"])
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 20)
        self.count_spin.setValue(5)
        self.generate_button = QPushButton("과년도 기출 기반 생성")
        self.generate_button.clicked.connect(self._run_generation)
        controls.addWidget(self.question_type_combo)
        controls.addWidget(self.count_spin)
        controls.addWidget(self.generate_button)
        self.generate_output = QTextEdit()
        self.generate_output.setReadOnly(True)
        self.generate_output.setMinimumHeight(140)
        layout.addWidget(self.topic_input)
        layout.addLayout(controls)
        layout.addWidget(self.generate_output)
        return group

    def _select_files(self) -> None:
        """기출 파일을 QFileDialog로 선택합니다."""
        files, _ = QFileDialog.getOpenFileNames(self, "과년도 기출 파일 선택", "", SUPPORTED_FILE_FILTER)
        self._add_files([Path(file) for file in files])

    def _select_folder(self) -> None:
        """기출 파일이 들어 있는 폴더를 선택 목록에 추가합니다."""
        folder = QFileDialog.getExistingDirectory(self, "과년도 기출 폴더 선택")
        if not folder:
            return
        files = self.indexer.collect_supported_files([Path(folder)])
        self._add_files(files)
        self.register_log.append(f"폴더 선택: {folder}")
        self.register_log.append(f"하위 폴더 포함 지원 기출 파일 {len(files)}개를 찾았습니다.")

    def _add_files(self, paths: list[Path]) -> None:
        """선택한 기출 파일을 중복 없이 목록에 추가합니다."""
        for path in paths:
            resolved = path.resolve()
            if resolved not in self.selected_files:
                self.selected_files.append(resolved)
                self.file_list.addItem(str(resolved))

    def _register_files_auto(self) -> None:
        """파일명 또는 본문에서 연도/회차를 추출해 기출 파일을 등록합니다."""
        if not self.selected_files:
            QMessageBox.warning(self, "과년도 기출 등록", "등록할 기출 파일 또는 폴더를 선택하세요.")
            return

        def task(progress_callback=None, log_callback=None) -> PastExamIndexReport:
            """자동 연도/회차 추출 기반 기출 등록 서비스를 호출합니다."""
            return PastExamIndexer().index_files_auto_metadata(
                self.selected_files,
                progress_callback,
                log_callback,
                use_llm_classification=self.llm_classify_checkbox.isChecked(),
            )

        self._run_worker(task, self.register_log, self._show_register_result)

    def _register_files(self) -> None:
        """선택한 기출 파일 등록을 백그라운드로 실행합니다."""
        if not self.selected_files:
            QMessageBox.warning(self, "과년도 기출 등록", "등록할 기출 파일을 선택하세요.")
            return
        year = int(self.year_combo.currentText())
        round_number = int(self.round_combo.currentText().replace("회", ""))

        def task(progress_callback=None, log_callback=None) -> PastExamIndexReport:
            """기출 등록 서비스를 호출합니다."""
            return PastExamIndexer().index_files(
                year,
                round_number,
                self.selected_files,
                progress_callback,
                log_callback,
                use_llm_classification=self.llm_classify_checkbox.isChecked(),
            )

        self._run_worker(task, self.register_log, self._show_register_result)

    def _reset_past_exam_data(self) -> None:
        """과년도 기출 데이터만 초기화합니다."""
        reply = QMessageBox.question(
            self,
            "기출 데이터 초기화",
            "과년도 기출 파일, 기출 JSON 인덱스, 벡터DB의 기출 Chunk를 삭제합니다.\n"
            "일반 문서 RAG 데이터는 유지됩니다.\n\n"
            "계속할까요?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        def task(progress_callback=None, log_callback=None) -> PastExamResetReport:
            """과년도 기출 초기화 서비스를 호출합니다."""
            if log_callback:
                log_callback("과년도 기출 데이터 초기화 중...")
            return PastExamIndexer().reset_past_exam_data()

        self._run_worker(task, self.register_log, self._show_reset_result)

    def _run_frequency_analysis(self) -> None:
        """기출 JSON 인덱스 기반 빈도 분석을 실행합니다."""
        period = self.analysis_period_combo.currentText()
        basis = "전체" if period == "전체 기간" else period
        value = self.analysis_year_combo.currentText() if period == "특정 연도" else ""
        category_text = self.analysis_category_combo.currentText()
        category = "" if category_text == "전체 과목" else category_text

        def task(progress_callback=None, log_callback=None) -> str:
            """Python 통계/흐름/관계 분석 서비스를 호출합니다."""
            indexer = PastExamIndexer()
            records = indexer.load_exam_records()
            if not records:
                legacy_records = indexer.load_index_records()
                analyzer = FrequencyAnalyzer()
                return analyzer.format_report(analyzer.analyze(legacy_records, basis=basis, value=value, category=category))

            records = self._filter_structured_records(records, basis, value, category)
            stats_engine = StatisticsEngine()
            stats = stats_engine.analyze(records)
            tree_builder = ExamTreeBuilder()
            tree = tree_builder.build(records)
            tree_path = tree_builder.save(tree)
            flow_analyzer = FlowAnalyzer()
            flow = flow_analyzer.analyze(records)
            flow_path = flow_analyzer.save(flow)
            gap_analyzer = GapAnalyzer()
            gap = gap_analyzer.analyze(records)
            gap_path = gap_analyzer.save(gap)
            cycle_analyzer = CycleAnalyzer()
            cycle = cycle_analyzer.analyze(records)
            cycle_path = cycle_analyzer.save(cycle)
            stability_analyzer = StabilityAnalyzer()
            stability = stability_analyzer.analyze(records)
            cluster_analyzer = TopicClusterAnalyzer()
            clusters = cluster_analyzer.analyze(records)
            prediction_analyzer = PredictionAnalyzer()
            predictions = prediction_analyzer.analyze(
                records,
                gap_scores=gap_analyzer.gap_scores(gap),
                stability_scores=stability_analyzer.score_map(stability),
                cluster_scores=cluster_analyzer.cluster_score_map(clusters),
                recent_change=stats.get("recent3_change", {}),
            )
            relation_analyzer = RelationAnalyzer()
            relations = relation_analyzer.analyze(records)
            relation_path = relation_analyzer.save_graph(relations)
            chart_paths = stats_engine.generate_charts(stats)
            chart_text = "\n".join(f"- {path}" for path in chart_paths) or "- 생성된 그래프 없음"
            return "\n\n".join(
                [
                    stats_engine.format_report(stats),
                    tree_builder.format_report(tree),
                    flow_analyzer.format_report(flow),
                    gap_analyzer.format_report(gap),
                    cycle_analyzer.format_report(cycle),
                    stability_analyzer.format_report(stability),
                    cluster_analyzer.format_report(clusters),
                    prediction_analyzer.format_report(predictions),
                    relation_analyzer.format_report(relations),
                    self._format_priority_report(records, gap),
                    UnclassifiedReporter().format_report(records),
                    ClassificationValidator().format_invalid_report(),
                    "저장된 분석 JSON",
                    f"- 출제 트리: {tree_path}\n- 출제 흐름: {flow_path}\n- 출제 공백: {gap_path}\n- 출제 주기: {cycle_path}\n- 연관 그래프: {relation_path}",
                    "그래프 파일",
                    chart_text,
                ]
            )

        self._run_worker(task, self.analysis_output)

    def _run_exam_tree(self) -> None:
        """출제 트리 JSON을 생성하고 출력합니다."""
        def task(progress_callback=None, log_callback=None) -> str:
            records = PastExamIndexer().load_exam_records()
            builder = ExamTreeBuilder()
            tree = builder.build(records)
            path = builder.save(tree)
            return builder.format_report(tree) + f"\n\n저장 위치: {path}"

        self._run_worker(task, self.coach_output)

    def _format_priority_report(self, records: list[dict], gap: dict) -> str:
        """공부 우선순위를 분석 출력용 문자열로 변환합니다."""
        gap_scores = GapAnalyzer().gap_scores(gap)
        priorities = StudyCoach().priorities(records, gap_scores=gap_scores)
        lines = ["공부 우선순위"]
        if not priorities:
            lines.append("- 데이터 없음")
            return "\n".join(lines)
        for item in priorities[:15]:
            lines.append(
                f"- {item['subcategory']}: {item['stars']} / score={item['score']} / "
                f"빈도 {item['frequency']}회, 최근 {item['recent']}회, 공백 {item['gap']}회, 연관 {item['related']}개"
            )
        return "\n".join(lines)

    def _run_exam_flow(self) -> None:
        """출제 흐름 JSON을 생성하고 출력합니다."""
        def task(progress_callback=None, log_callback=None) -> str:
            records = PastExamIndexer().load_exam_records()
            analyzer = FlowAnalyzer()
            analysis = analyzer.analyze(records)
            path = analyzer.save(analysis)
            return analyzer.format_report(analysis) + f"\n\n저장 위치: {path}"

        self._run_worker(task, self.coach_output)

    def _run_relation_graph(self) -> None:
        """연관 개념 그래프 JSON을 생성하고 출력합니다."""
        def task(progress_callback=None, log_callback=None) -> str:
            records = PastExamIndexer().load_exam_records()
            analyzer = RelationAnalyzer()
            groups = analyzer.analyze(records)
            path = analyzer.save_graph(groups)
            return analyzer.format_report(groups) + f"\n\n저장 위치: {path}"

        self._run_worker(task, self.coach_output)

    def _run_gap_analysis(self) -> None:
        """출제 공백 분석 JSON을 생성하고 출력합니다."""
        def task(progress_callback=None, log_callback=None) -> str:
            records = PastExamIndexer().load_exam_records()
            analyzer = GapAnalyzer()
            analysis = analyzer.analyze(records)
            path = analyzer.save(analysis)
            return analyzer.format_report(analysis) + f"\n\n저장 위치: {path}"

        self._run_worker(task, self.coach_output)

    def _run_cycle_analysis(self) -> None:
        """출제 주기 분석 JSON을 생성하고 출력합니다."""
        def task(progress_callback=None, log_callback=None) -> str:
            records = PastExamIndexer().load_exam_records()
            analyzer = CycleAnalyzer()
            analysis = analyzer.analyze(records)
            path = analyzer.save(analysis)
            return analyzer.format_report(analysis) + f"\n\n저장 위치: {path}"

        self._run_worker(task, self.coach_output)

    def _run_stability_analysis(self) -> None:
        """출제 안정도를 출력합니다."""
        def task(progress_callback=None, log_callback=None) -> str:
            records = PastExamIndexer().load_exam_records()
            analyzer = StabilityAnalyzer()
            return analyzer.format_report(analyzer.analyze(records))

        self._run_worker(task, self.coach_output)

    def _run_topic_cluster(self) -> None:
        """Topic Cluster를 출력합니다."""
        def task(progress_callback=None, log_callback=None) -> str:
            records = PastExamIndexer().load_exam_records()
            analyzer = TopicClusterAnalyzer()
            return analyzer.format_report(analyzer.analyze(records))

        self._run_worker(task, self.coach_output)

    def _run_prediction_analysis(self) -> None:
        """기출 기반 출제 가능성 점수를 출력합니다."""
        def task(progress_callback=None, log_callback=None) -> str:
            records = PastExamIndexer().load_exam_records()
            stats = StatisticsEngine().analyze(records)
            gap_analyzer = GapAnalyzer()
            gap = gap_analyzer.analyze(records)
            stability_analyzer = StabilityAnalyzer()
            stability = stability_analyzer.analyze(records)
            cluster_analyzer = TopicClusterAnalyzer()
            clusters = cluster_analyzer.analyze(records)
            analyzer = PredictionAnalyzer()
            predictions = analyzer.analyze(
                records,
                gap_scores=gap_analyzer.gap_scores(gap),
                stability_scores=stability_analyzer.score_map(stability),
                cluster_scores=cluster_analyzer.cluster_score_map(clusters),
                recent_change=stats.get("recent3_change", {}),
            )
            return analyzer.format_report(predictions)

        self._run_worker(task, self.coach_output)

    def _run_coverage(self) -> None:
        """완료 키워드 기준 출제 커버리지를 계산합니다."""
        completed_topics = self._completed_topics()

        def task(progress_callback=None, log_callback=None) -> dict:
            records = PastExamIndexer().load_exam_records()
            tree = ExamTreeBuilder().build(records)
            analysis = CoverageAnalyzer().analyze(tree, completed_topics)
            return {"text": CoverageAnalyzer().format_report(analysis), "coverage": analysis["coverage"]}

        self._run_worker(task, self.coach_output, self._show_coverage_result)

    def _run_today_study(self) -> None:
        """오늘 공부 추천을 출력합니다."""
        exam_date = self._selected_exam_date()
        hours = float(self.study_hours_spin.value())

        def task(progress_callback=None, log_callback=None) -> str:
            records = PastExamIndexer().load_exam_records()
            gap_scores = GapAnalyzer().gap_scores(GapAnalyzer().analyze(records))
            return StudyCoach().today(records, exam_date=exam_date, hours=hours, gap_scores=gap_scores)

        self._run_worker(task, self.coach_output)

    def _run_roadmap(self) -> None:
        """시험일까지 학습 로드맵을 출력합니다."""
        exam_date = self._selected_exam_date()
        hours = float(self.study_hours_spin.value())

        def task(progress_callback=None, log_callback=None) -> str:
            records = PastExamIndexer().load_exam_records()
            gap_scores = GapAnalyzer().gap_scores(GapAnalyzer().analyze(records))
            return StudyCoach().roadmap(records, exam_date=exam_date, hours_per_day=hours, gap_scores=gap_scores)

        self._run_worker(task, self.coach_output)

    def _run_wrong_answer(self) -> None:
        """오답 키워드 기반 복습 추천을 출력합니다."""
        wrong_text = self.wrong_answer_input.toPlainText().strip()
        if not wrong_text:
            QMessageBox.warning(self, "오답 분석", "오답 키워드를 입력하세요.")
            return

        def task(progress_callback=None, log_callback=None) -> str:
            records = PastExamIndexer().load_exam_records()
            return StudyCoach().wrong_answer_report(records, wrong_text)

        self._run_worker(task, self.coach_output)

    def _selected_exam_date(self) -> date:
        """GUI의 시험일 입력값을 date로 변환합니다."""
        selected = self.exam_date_input.date()
        return date(selected.year(), selected.month(), selected.day())

    def _completed_topics(self) -> set[str]:
        """입력창에서 공부 완료 키워드를 추출합니다."""
        raw_text = self.wrong_answer_input.toPlainText()
        return {item.strip() for item in raw_text.replace("\n", ",").split(",") if item.strip()}

    def _show_coverage_result(self, result: dict) -> None:
        """커버리지 결과를 ProgressBar와 출력창에 표시합니다."""
        self.coverage_progress.setValue(int(result.get("coverage") or 0))
        self.coach_output.setPlainText(str(result.get("text") or ""))

    def _filter_structured_records(
        self,
        records: list[dict],
        basis: str,
        value: str,
        subject: str,
    ) -> list[dict]:
        """GUI 분석 필터를 구조화 레코드에 적용합니다."""
        filtered = records
        if basis == "최근 3개년":
            years = sorted({int(record.get("year") or 0) for record in filtered if record.get("year")}, reverse=True)
            filtered = [record for record in filtered if int(record.get("year") or 0) in set(years[:3])]
        elif basis == "특정 연도" and value:
            filtered = [record for record in filtered if str(record.get("year")) == str(value)]
        if subject:
            filtered = [record for record in filtered if record.get("subject") == subject]
        return filtered

    def _run_strategy(self) -> None:
        """다음 시험 대비 전략 생성을 실행합니다."""
        def task(progress_callback=None, log_callback=None) -> str:
            """전략 분석 서비스를 호출합니다."""
            indexer = PastExamIndexer()
            records = indexer.load_exam_records() or indexer.load_index_records()
            return ExamStrategyAnalyzer().generate_strategy(records)

        self._run_worker(task, self.strategy_output)

    def _run_generation(self) -> None:
        """과년도 기출 기반 예상문제를 생성합니다."""
        topic = self.topic_input.toPlainText().strip()
        if not topic:
            QMessageBox.warning(self, "예상문제 생성", "주제를 입력하세요.")
            return

        def task(progress_callback=None, log_callback=None) -> str:
            """기출 기반 예상문제 생성 서비스를 호출합니다."""
            return ExpectedQuestionGenerator().generate_from_past_exams(
                topic=topic,
                question_type=self.question_type_combo.currentText(),
                count=self.count_spin.value(),
                mode="과년도 기출 기반",
            )

        self._run_worker(task, self.generate_output)

    def _run_worker(self, task, output: QTextEdit, result_handler=None) -> None:
        """공통 Worker 실행 흐름을 처리합니다."""
        if self.thread is not None and self.thread.isRunning():
            QMessageBox.warning(self, "작업 진행 중", "현재 작업이 완료된 뒤 다시 실행하세요.")
            return

        output.setPlainText("처리 중입니다...")
        self._set_running(True)

        thread = QThread(self)
        worker = Worker(task)
        self.thread = thread
        self.worker = worker
        self.worker_output = output
        self.worker_result_handler = result_handler
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log.connect(self._handle_worker_log)
        worker.result.connect(self._handle_worker_result)
        worker.error.connect(self._handle_worker_error)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._clear_worker(thread, worker))
        thread.start()

    def _show_register_result(self, report: PastExamIndexReport) -> None:
        """기출 등록 결과를 표시합니다."""
        self.register_log.append("\n" + report.to_message())
        QMessageBox.information(self, "과년도 기출 등록 완료", report.to_message())

    def _show_reset_result(self, report: PastExamResetReport) -> None:
        """기출 초기화 결과를 표시합니다."""
        self.selected_files.clear()
        self.file_list.clear()
        self.register_log.append("\n" + report.to_message())
        QMessageBox.information(self, "과년도 기출 초기화 완료", report.to_message())

    def _show_error(self, message: str, output: QTextEdit) -> None:
        """작업 오류를 메시지 박스와 출력창에 표시합니다."""
        output.append(f"오류: {message}")
        QMessageBox.critical(self, "과년도 기출 분석 오류", message)

    @Slot(str)
    def _handle_worker_log(self, message: str) -> None:
        """Worker 로그를 메인 스레드에서 출력합니다."""
        if self.worker_output is not None:
            self.worker_output.append(message)

    @Slot(object)
    def _handle_worker_result(self, result) -> None:
        """Worker 결과를 메인 스레드에서 출력합니다."""
        if self.worker_result_handler is not None:
            self.worker_result_handler(result)
            return
        if self.worker_output is not None:
            self.worker_output.setPlainText(str(result))

    @Slot(str)
    def _handle_worker_error(self, message: str) -> None:
        """Worker 오류를 메인 스레드에서 표시합니다."""
        if self.worker_output is not None:
            self._show_error(message, self.worker_output)

    def _set_running(self, running: bool) -> None:
        """기출 탭에서 백그라운드 작업 중 중복 실행을 막습니다."""
        for button in (
            self.file_button,
            self.folder_button,
            self.register_button,
            self.auto_register_button,
            self.reset_button,
            self.llm_classify_checkbox,
            self.analysis_button,
            self.strategy_button,
            self.tree_button,
            self.flow_button,
            self.relation_button,
            self.gap_button,
            self.cycle_button,
            self.stability_button,
            self.cluster_button,
            self.prediction_button,
            self.coverage_button,
            self.today_button,
            self.roadmap_button,
            self.wrong_answer_button,
            self.generate_button,
        ):
            button.setEnabled(not running)
        self.analysis_period_combo.setEnabled(not running)
        self.analysis_year_combo.setEnabled(not running and self.analysis_period_combo.currentText() == "특정 연도")
        self.analysis_category_combo.setEnabled(not running)

    def _clear_worker(self, thread: QThread, worker: Worker) -> None:
        """완료된 Worker 참조를 정리하고 버튼을 다시 활성화합니다."""
        if self.thread is thread:
            self.thread = None
        if self.worker is worker:
            self.worker = None
        self.worker_output = None
        self.worker_result_handler = None
        self._set_running(False)

    def _update_analysis_filters(self) -> None:
        """기간 선택에 따라 연도 필터 활성 상태를 조정합니다."""
        running = self.thread is not None and self.thread.isRunning()
        self.analysis_year_combo.setEnabled(not running and self.analysis_period_combo.currentText() == "특정 연도")
