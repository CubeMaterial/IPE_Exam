"""RAG 질문하기 탭을 제공합니다."""

from __future__ import annotations

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget

from src.rag.generator import RAGGenerator
from src.ui.worker import Worker


class ChatTab(QWidget):
    """질문 입력과 RAG 답변 출력을 담당하는 화면입니다."""

    def __init__(self) -> None:
        """질문하기 탭 UI를 초기화합니다."""
        super().__init__()
        self.thread: QThread | None = None
        self.worker: Worker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        """탭 화면 구성요소를 생성합니다."""
        layout = QVBoxLayout(self)
        self.question_input = QTextEdit()
        self.question_input.setPlaceholderText("질문을 입력하세요.")
        self.run_button = QPushButton("질문 실행")
        self.answer_output = QTextEdit()
        self.answer_output.setReadOnly(True)
        self.reference_output = QTextEdit()
        self.reference_output.setReadOnly(True)
        self.reference_output.setPlaceholderText("참고 문서가 여기에 표시됩니다.")

        self.run_button.clicked.connect(self._run_question)
        layout.addWidget(self.question_input)
        layout.addWidget(self.run_button)
        layout.addWidget(self.answer_output)
        layout.addWidget(self.reference_output)

    def _run_question(self) -> None:
        """백그라운드 Worker로 RAG 질문을 실행합니다."""
        question = self.question_input.toPlainText().strip()
        if not question:
            QMessageBox.warning(self, "질문하기", "질문을 입력하세요.")
            return

        self._set_running(True)
        self.answer_output.setPlainText("답변 생성 중입니다...")
        self.reference_output.clear()

        def task(progress_callback=None, log_callback=None) -> str:
            """RAG 답변 생성 서비스를 호출합니다."""
            if log_callback:
                log_callback("RAG 답변 생성 시작")
            return RAGGenerator().answer(question)

        self.thread = QThread()
        self.worker = Worker(task)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.result.connect(self._show_answer)
        self.worker.error.connect(self._show_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(lambda: self._set_running(False))
        self.thread.start()

    def _show_answer(self, answer: str) -> None:
        """답변과 참고 문서 영역을 분리해 표시합니다."""
        marker = "\n\n참고 문서:"
        if marker in answer:
            body, references = answer.split(marker, 1)
            self.answer_output.setPlainText(body)
            self.reference_output.setPlainText("참고 문서:" + references)
        else:
            self.answer_output.setPlainText(answer)

    def _show_error(self, message: str) -> None:
        """질문 처리 오류를 표시합니다."""
        self.answer_output.setPlainText("")
        QMessageBox.critical(self, "질문 오류", message)

    def _set_running(self, running: bool) -> None:
        """작업 중 버튼 활성 상태를 조정합니다."""
        self.run_button.setEnabled(not running)
