"""개념 분석과 문제 유형 분석 탭을 제공합니다."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QFileDialog, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget

from src.analyzer.concept_analyzer import ConceptAnalyzer
from src.analyzer.question_analyzer import QuestionAnalyzer
from src.loader.pdf_loader import PdfLoader
from src.loader.txt_loader import TxtLoader
from src.preprocess.cleaner import TextCleaner
from src.ui.worker import Worker


class ConceptAnalyzeTab(QWidget):
    """개념 분석 화면입니다."""

    def __init__(self) -> None:
        """개념 분석 탭 UI를 초기화합니다."""
        super().__init__()
        self.thread: QThread | None = None
        self.worker: Worker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        """탭 화면 구성요소를 생성합니다."""
        layout = QVBoxLayout(self)
        self.input = QTextEdit()
        self.input.setPlaceholderText("분석할 개념을 입력하세요. 예: C언어 포인터 정리")
        self.button = QPushButton("분석")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.button.clicked.connect(self._run_analysis)
        layout.addWidget(self.input)
        layout.addWidget(self.button)
        layout.addWidget(self.output)

    def _run_analysis(self) -> None:
        """백그라운드 Worker로 개념 분석을 실행합니다."""
        concept = self.input.toPlainText().strip()
        if not concept:
            QMessageBox.warning(self, "개념 분석", "분석할 개념을 입력하세요.")
            return
        self._run_worker(lambda **_: ConceptAnalyzer().analyze(concept))

    def _run_worker(self, task) -> None:
        """공통 Worker 실행 흐름을 처리합니다."""
        self.button.setEnabled(False)
        self.output.setPlainText("분석 중입니다...")
        self.thread = QThread()
        self.worker = Worker(task)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.result.connect(lambda result: self.output.setPlainText(str(result)))
        self.worker.error.connect(self._show_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(lambda: self.button.setEnabled(True))
        self.thread.start()

    def _show_error(self, message: str) -> None:
        """분석 오류를 표시합니다."""
        self.output.clear()
        QMessageBox.critical(self, "개념 분석 오류", message)


class QuestionAnalyzeTab(QWidget):
    """문제 유형 분석 화면입니다."""

    def __init__(self) -> None:
        """문제 유형 분석 탭 UI를 초기화합니다."""
        super().__init__()
        self.thread: QThread | None = None
        self.worker: Worker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        """탭 화면 구성요소를 생성합니다."""
        layout = QVBoxLayout(self)
        self.input = QTextEdit()
        self.input.setPlaceholderText("분석할 기출문제를 입력하거나 파일에서 불러오세요.")
        self.load_button = QPushButton("파일에서 문제 불러오기")
        self.button = QPushButton("분석")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.load_button.clicked.connect(self._load_question_file)
        self.button.clicked.connect(self._run_analysis)
        layout.addWidget(self.input)
        layout.addWidget(self.load_button)
        layout.addWidget(self.button)
        layout.addWidget(self.output)

    def _load_question_file(self) -> None:
        """TXT 또는 PDF 파일에서 문제 텍스트를 불러옵니다."""
        file, _ = QFileDialog.getOpenFileName(self, "문제 파일 선택", "", "문제 파일 (*.txt *.pdf)")
        if not file:
            return
        try:
            path = Path(file)
            if path.suffix.lower() == ".txt":
                text = TxtLoader().load(path)
            else:
                text = PdfLoader().load(path).text
            self.input.setPlainText(TextCleaner().clean(text))
        except Exception as exc:
            QMessageBox.critical(self, "파일 불러오기 오류", str(exc))

    def _run_analysis(self) -> None:
        """백그라운드 Worker로 문제 유형 분석을 실행합니다."""
        question = self.input.toPlainText().strip()
        if not question:
            QMessageBox.warning(self, "문제 유형 분석", "분석할 문제를 입력하세요.")
            return
        self._run_worker(lambda **_: QuestionAnalyzer().analyze(question))

    def _run_worker(self, task) -> None:
        """공통 Worker 실행 흐름을 처리합니다."""
        self.button.setEnabled(False)
        self.load_button.setEnabled(False)
        self.output.setPlainText("분석 중입니다...")
        self.thread = QThread()
        self.worker = Worker(task)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.result.connect(lambda result: self.output.setPlainText(str(result)))
        self.worker.error.connect(self._show_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(lambda: self._set_running(False))
        self.thread.start()

    def _show_error(self, message: str) -> None:
        """문제 분석 오류를 표시합니다."""
        self.output.clear()
        QMessageBox.critical(self, "문제 분석 오류", message)

    def _set_running(self, running: bool) -> None:
        """작업 중 버튼 활성 상태를 조정합니다."""
        self.button.setEnabled(not running)
        self.load_button.setEnabled(not running)
