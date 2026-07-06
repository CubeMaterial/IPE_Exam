"""문서 등록 탭을 제공합니다."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.rag.document_indexer import DocumentIndexer, IndexReport
from src.ui.worker import Worker


SUPPORTED_FILE_FILTER = (
    "PDF/Text/Image/ZIP/Code Files "
    "(*.pdf *.txt *.png *.jpg *.jpeg *.zip "
    "*.c *.h *.cpp *.hpp *.java *.py *.dart *.js *.ts *.kt *.swift *.go *.rs *.cs)"
)


class DocumentTab(QWidget):
    """파일/폴더/ZIP 문서 등록 화면입니다."""

    def __init__(self) -> None:
        """문서 등록 탭 UI를 초기화합니다."""
        super().__init__()
        self.selected_paths: list[Path] = []
        self.indexer = DocumentIndexer()
        self.thread: QThread | None = None
        self.worker: Worker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        """탭 화면 구성요소를 생성합니다."""
        layout = QVBoxLayout(self)
        button_layout = QHBoxLayout()

        self.file_button = QPushButton("파일 선택")
        self.folder_button = QPushButton("폴더 선택")
        self.zip_button = QPushButton("ZIP 선택")
        self.start_button = QPushButton("등록 시작")

        self.file_button.clicked.connect(self._select_files)
        self.folder_button.clicked.connect(self._select_folder)
        self.zip_button.clicked.connect(self._select_zip)
        self.start_button.clicked.connect(self._start_indexing)

        for button in (self.file_button, self.folder_button, self.zip_button, self.start_button):
            button_layout.addWidget(button)

        self.file_list = QListWidget()
        self.progress_bar = QProgressBar()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        layout.addLayout(button_layout)
        layout.addWidget(self.file_list)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_output)

    def _select_files(self) -> None:
        """지원 문서 파일을 선택 목록에 추가합니다."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "문서 파일 선택",
            "",
            SUPPORTED_FILE_FILTER,
        )
        self._add_paths([Path(file) for file in files])

    def _select_folder(self) -> None:
        """문서가 들어 있는 폴더를 선택 목록에 추가합니다."""
        folder = QFileDialog.getExistingDirectory(self, "문서 폴더 선택")
        if folder:
            files = self.indexer.collect_supported_files([Path(folder)])
            self._add_paths(files)
            self.log_output.append(f"폴더 선택: {folder}")
            self.log_output.append(f"하위 폴더 포함 지원 문서 {len(files)}개를 찾았습니다.")

    def _select_zip(self) -> None:
        """ZIP 파일을 선택 목록에 추가합니다."""
        file, _ = QFileDialog.getOpenFileName(self, "ZIP 파일 선택", "", "ZIP (*.zip)")
        if file:
            self._add_paths([Path(file)])

    def _add_paths(self, paths: list[Path]) -> None:
        """선택한 경로를 중복 없이 목록에 추가합니다."""
        for path in paths:
            if path not in self.selected_paths:
                self.selected_paths.append(path)
                self.file_list.addItem(str(path))

    def _start_indexing(self) -> None:
        """백그라운드 Worker로 문서 등록을 시작합니다."""
        if not self.selected_paths:
            QMessageBox.warning(self, "문서 등록", "등록할 파일 또는 폴더를 먼저 선택하세요.")
            return

        self._set_running(True)
        self.progress_bar.setValue(0)
        self.log_output.clear()

        def task(progress_callback=None, log_callback=None) -> IndexReport:
            """문서 등록 서비스를 호출합니다."""
            return DocumentIndexer().index_paths(self.selected_paths, progress_callback, log_callback)

        self.thread = QThread()
        self.worker = Worker(task)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self._append_log)
        self.worker.result.connect(self._show_result)
        self.worker.error.connect(self._show_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(lambda: self._set_running(False))
        self.thread.start()

    def _append_log(self, message: str) -> None:
        """처리 로그를 화면에 추가합니다."""
        self.log_output.append(message)

    def _show_result(self, report: IndexReport) -> None:
        """문서 등록 완료 결과를 표시합니다."""
        self.progress_bar.setValue(100)
        self.log_output.append("\n" + report.to_message())
        QMessageBox.information(self, "문서 등록 완료", report.to_message())

    def _show_error(self, message: str) -> None:
        """문서 등록 오류를 표시합니다."""
        self.log_output.append(f"오류: {message}")
        QMessageBox.critical(self, "문서 등록 오류", message)

    def _set_running(self, running: bool) -> None:
        """작업 중 버튼 활성 상태를 조정합니다."""
        for button in (self.file_button, self.folder_button, self.zip_button, self.start_button):
            button.setEnabled(not running)
