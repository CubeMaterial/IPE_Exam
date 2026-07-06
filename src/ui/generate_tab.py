"""예상문제 생성 탭을 제공합니다."""

from __future__ import annotations

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QMessageBox, QPushButton, QSpinBox, QTextEdit, QVBoxLayout, QWidget

from src.generator.expected_question_generator import ExpectedQuestionGenerator
from src.ui.worker import Worker


class GenerateTab(QWidget):
    """예상문제 생성 화면입니다."""

    def __init__(self) -> None:
        """예상문제 생성 탭 UI를 초기화합니다."""
        super().__init__()
        self.thread: QThread | None = None
        self.worker: Worker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        """탭 화면 구성요소를 생성합니다."""
        layout = QVBoxLayout(self)
        control_layout = QHBoxLayout()
        self.topic_input = QTextEdit()
        self.topic_input.setPlaceholderText("예상문제를 만들 주제 또는 기준 자료를 입력하세요.")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["객관식", "주관식", "코드 출력", "SQL", "OX", "빈칸"])
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 20)
        self.count_spin.setValue(3)
        self.button = QPushButton("생성")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.button.clicked.connect(self._run_generation)
        control_layout.addWidget(self.type_combo)
        control_layout.addWidget(self.count_spin)
        control_layout.addWidget(self.button)
        layout.addWidget(self.topic_input)
        layout.addLayout(control_layout)
        layout.addWidget(self.output)

    def _run_generation(self) -> None:
        """백그라운드 Worker로 예상문제를 생성합니다."""
        topic = self.topic_input.toPlainText().strip()
        if not topic:
            QMessageBox.warning(self, "예상문제 생성", "주제를 입력하세요.")
            return
        question_type = self.type_combo.currentText()
        count = self.count_spin.value()
        prompt = f"{topic}\n\n문제 수: {count}개"
        self._run_worker(lambda **_: ExpectedQuestionGenerator().generate(prompt, question_type))

    def _run_worker(self, task) -> None:
        """공통 Worker 실행 흐름을 처리합니다."""
        self.button.setEnabled(False)
        self.output.setPlainText("생성 중입니다...")
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
        """예상문제 생성 오류를 표시합니다."""
        self.output.clear()
        QMessageBox.critical(self, "예상문제 생성 오류", message)
