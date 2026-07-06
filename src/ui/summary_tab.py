"""학습 자료 요약 탭을 제공합니다."""

from __future__ import annotations

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QComboBox, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget

from src.rag.generator import RAGGenerator
from src.ui.worker import Worker


class SummaryTab(QWidget):
    """등록된 자료를 기반으로 요약을 생성하는 화면입니다."""

    def __init__(self) -> None:
        """요약 탭 UI를 초기화합니다."""
        super().__init__()
        self.thread: QThread | None = None
        self.worker: Worker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        """탭 화면 구성요소를 생성합니다."""
        layout = QVBoxLayout(self)
        self.topic_input = QTextEdit()
        self.topic_input.setPlaceholderText("요약할 주제, 문서명, Chapter 또는 범위를 입력하세요.")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["3줄 요약", "10줄 요약", "시험용 암기 요약"])
        self.button = QPushButton("요약")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.button.clicked.connect(self._run_summary)
        layout.addWidget(self.topic_input)
        layout.addWidget(self.type_combo)
        layout.addWidget(self.button)
        layout.addWidget(self.output)

    def _run_summary(self) -> None:
        """백그라운드 Worker로 요약을 생성합니다."""
        topic = self.topic_input.toPlainText().strip()
        if not topic:
            QMessageBox.warning(self, "요약", "요약할 주제를 입력하세요.")
            return
        summary_type = self.type_combo.currentText()
        self._run_worker(lambda **_: RAGGenerator().summarize(topic, summary_type))

    def _run_worker(self, task) -> None:
        """공통 Worker 실행 흐름을 처리합니다."""
        self.button.setEnabled(False)
        self.output.setPlainText("요약 중입니다...")
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
        """요약 오류를 표시합니다."""
        self.output.clear()
        QMessageBox.critical(self, "요약 오류", message)
