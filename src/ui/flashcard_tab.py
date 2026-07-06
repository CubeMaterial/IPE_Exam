"""암기 카드 생성 탭을 제공합니다."""

from __future__ import annotations

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QHBoxLayout, QMessageBox, QPushButton, QSpinBox, QTextEdit, QVBoxLayout, QWidget

from src.rag.generator import RAGGenerator
from src.ui.worker import Worker


class FlashcardTab(QWidget):
    """Q/A 형식의 암기 카드를 생성하는 화면입니다."""

    def __init__(self) -> None:
        """암기 카드 탭 UI를 초기화합니다."""
        super().__init__()
        self.thread: QThread | None = None
        self.worker: Worker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        """탭 화면 구성요소를 생성합니다."""
        layout = QVBoxLayout(self)
        control_layout = QHBoxLayout()
        self.topic_input = QTextEdit()
        self.topic_input.setPlaceholderText("암기 카드로 만들 주제를 입력하세요.")
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 50)
        self.count_spin.setValue(10)
        self.button = QPushButton("생성")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.button.clicked.connect(self._run_flashcards)
        control_layout.addWidget(self.count_spin)
        control_layout.addWidget(self.button)
        layout.addWidget(self.topic_input)
        layout.addLayout(control_layout)
        layout.addWidget(self.output)

    def _run_flashcards(self) -> None:
        """백그라운드 Worker로 암기 카드를 생성합니다."""
        topic = self.topic_input.toPlainText().strip()
        if not topic:
            QMessageBox.warning(self, "암기 카드", "주제를 입력하세요.")
            return
        request = f"{topic}\n\n카드 수: {self.count_spin.value()}개\n출력 형식은 반드시 Q: 와 A: 를 사용하세요."
        self._run_worker(lambda **_: RAGGenerator().make_flashcards(request))

    def _run_worker(self, task) -> None:
        """공통 Worker 실행 흐름을 처리합니다."""
        self.button.setEnabled(False)
        self.output.setPlainText("암기 카드 생성 중입니다...")
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
        """암기 카드 생성 오류를 표시합니다."""
        self.output.clear()
        QMessageBox.critical(self, "암기 카드 오류", message)
