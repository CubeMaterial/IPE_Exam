"""과년도 기출 분석 탭을 제공합니다."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.analyzer.exam_strategy_analyzer import ExamStrategyAnalyzer
from src.analyzer.frequency_analyzer import FrequencyAnalyzer
from src.analyzer.past_exam_indexer import PastExamIndexer, PastExamIndexReport
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
        self.indexer = PastExamIndexer()
        self._build_ui()

    def _build_ui(self) -> None:
        """탭 화면 구성요소를 생성합니다."""
        layout = QVBoxLayout(self)
        layout.addWidget(self._registration_group())
        layout.addWidget(self._analysis_group())
        layout.addWidget(self._strategy_group())
        layout.addWidget(self._generation_group())

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
        self.register_button = QPushButton("등록")
        self.file_button.clicked.connect(self._select_files)
        self.register_button.clicked.connect(self._register_files)
        controls.addWidget(self.year_combo)
        controls.addWidget(self.round_combo)
        controls.addWidget(self.file_button)
        controls.addWidget(self.register_button)
        self.file_list = QListWidget()
        self.register_log = QTextEdit()
        self.register_log.setReadOnly(True)
        layout.addLayout(controls)
        layout.addWidget(self.file_list)
        layout.addWidget(self.register_log)
        return group

    def _analysis_group(self) -> QGroupBox:
        """빈도 분석 영역을 생성합니다."""
        group = QGroupBox("분석")
        layout = QVBoxLayout(group)
        controls = QHBoxLayout()
        self.analysis_basis_combo = QComboBox()
        self.analysis_basis_combo.addItems(["전체", "최근 3개년", "특정 연도", "특정 과목"])
        self.analysis_value_combo = QComboBox()
        self.analysis_value_combo.addItems(["", "2020", "2021", "2022", "2023", "2024", "2025", "2026", "프로그래밍 언어 활용", "SQL 응용", "소프트웨어 개발 보안 구축", "응용 SW 기초 기술 활용"])
        self.analysis_button = QPushButton("분석 실행")
        self.analysis_button.clicked.connect(self._run_frequency_analysis)
        controls.addWidget(self.analysis_basis_combo)
        controls.addWidget(self.analysis_value_combo)
        controls.addWidget(self.analysis_button)
        self.analysis_output = QTextEdit()
        self.analysis_output.setReadOnly(True)
        layout.addLayout(controls)
        layout.addWidget(self.analysis_output)
        return group

    def _strategy_group(self) -> QGroupBox:
        """다음 시험 대비 전략 영역을 생성합니다."""
        group = QGroupBox("전략")
        layout = QVBoxLayout(group)
        self.strategy_button = QPushButton("다음 시험 대비 전략 생성")
        self.strategy_button.clicked.connect(self._run_strategy)
        self.strategy_output = QTextEdit()
        self.strategy_output.setReadOnly(True)
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
        layout.addWidget(self.topic_input)
        layout.addLayout(controls)
        layout.addWidget(self.generate_output)
        return group

    def _select_files(self) -> None:
        """기출 파일을 QFileDialog로 선택합니다."""
        files, _ = QFileDialog.getOpenFileNames(self, "과년도 기출 파일 선택", "", SUPPORTED_FILE_FILTER)
        for file in files:
            path = Path(file)
            if path not in self.selected_files:
                self.selected_files.append(path)
                self.file_list.addItem(str(path))

    def _register_files(self) -> None:
        """선택한 기출 파일 등록을 백그라운드로 실행합니다."""
        if not self.selected_files:
            QMessageBox.warning(self, "과년도 기출 등록", "등록할 기출 파일을 선택하세요.")
            return
        year = int(self.year_combo.currentText())
        round_number = int(self.round_combo.currentText().replace("회", ""))

        def task(progress_callback=None, log_callback=None) -> PastExamIndexReport:
            """기출 등록 서비스를 호출합니다."""
            return PastExamIndexer().index_files(year, round_number, self.selected_files, progress_callback, log_callback)

        self._run_worker(task, self.register_log, self._show_register_result)

    def _run_frequency_analysis(self) -> None:
        """기출 JSON 인덱스 기반 빈도 분석을 실행합니다."""
        basis = self.analysis_basis_combo.currentText()
        value = self.analysis_value_combo.currentText()

        def task(progress_callback=None, log_callback=None) -> str:
            """빈도 분석 서비스를 호출합니다."""
            records = PastExamIndexer().load_index_records()
            analyzer = FrequencyAnalyzer()
            return analyzer.format_report(analyzer.analyze(records, basis=basis, value=value))

        self._run_worker(task, self.analysis_output)

    def _run_strategy(self) -> None:
        """다음 시험 대비 전략 생성을 실행합니다."""
        def task(progress_callback=None, log_callback=None) -> str:
            """전략 분석 서비스를 호출합니다."""
            records = PastExamIndexer().load_index_records()
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
        output.setPlainText("처리 중입니다...")
        self.thread = QThread()
        self.worker = Worker(task)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(lambda message: output.append(message))
        self.worker.result.connect(result_handler or (lambda result: output.setPlainText(str(result))))
        self.worker.error.connect(lambda message: self._show_error(message, output))
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _show_register_result(self, report: PastExamIndexReport) -> None:
        """기출 등록 결과를 표시합니다."""
        self.register_log.append("\n" + report.to_message())
        QMessageBox.information(self, "과년도 기출 등록 완료", report.to_message())

    def _show_error(self, message: str, output: QTextEdit) -> None:
        """작업 오류를 메시지 박스와 출력창에 표시합니다."""
        output.append(f"오류: {message}")
        QMessageBox.critical(self, "과년도 기출 분석 오류", message)
