"""설정 탭을 제공합니다."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QWidget,
)

from config.config import CONFIG, save_env_config, update_runtime_config


class SettingsTab(QWidget):
    """Ollama, Chunk, ChromaDB, OCR 설정 화면입니다."""

    def __init__(self) -> None:
        """설정 탭 UI를 초기화합니다."""
        super().__init__()
        self._build_ui()

    def _build_ui(self) -> None:
        """탭 화면 구성요소를 생성합니다."""
        layout = QFormLayout(self)
        self.ollama_model_input = QLineEdit(CONFIG.ollama_model)
        self.embedding_model_input = QLineEdit(CONFIG.embedding_model)
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(100, 10000)
        self.chunk_size_spin.setValue(CONFIG.chunk_size)
        self.chunk_overlap_spin = QSpinBox()
        self.chunk_overlap_spin.setRange(0, 5000)
        self.chunk_overlap_spin.setValue(CONFIG.chunk_overlap)
        self.chroma_path_input = QLineEdit(str(CONFIG.chroma_dir))
        self.ocr_checkbox = QCheckBox("OCR 사용")
        self.ocr_checkbox.setChecked(CONFIG.ocr_enabled)
        self.save_button = QPushButton("설정 저장")
        self.save_button.clicked.connect(self._save_settings)

        path_layout = QHBoxLayout()
        browse_button = QPushButton("경로 선택")
        browse_button.clicked.connect(self._select_chroma_path)
        path_layout.addWidget(self.chroma_path_input)
        path_layout.addWidget(browse_button)

        layout.addRow("Ollama 모델명", self.ollama_model_input)
        layout.addRow("Embedding 모델명", self.embedding_model_input)
        layout.addRow("Chunk Size", self.chunk_size_spin)
        layout.addRow("Chunk Overlap", self.chunk_overlap_spin)
        layout.addRow("ChromaDB 경로", path_layout)
        layout.addRow("OCR", self.ocr_checkbox)
        layout.addRow(self.save_button)

    def _select_chroma_path(self) -> None:
        """ChromaDB 저장 폴더를 선택합니다."""
        folder = QFileDialog.getExistingDirectory(self, "ChromaDB 경로 선택", self.chroma_path_input.text())
        if folder:
            self.chroma_path_input.setText(folder)

    def _save_settings(self) -> None:
        """설정값을 런타임과 .env 파일에 반영합니다."""
        chunk_size = self.chunk_size_spin.value()
        chunk_overlap = self.chunk_overlap_spin.value()
        if chunk_overlap >= chunk_size:
            QMessageBox.warning(self, "설정 오류", "Chunk Overlap은 Chunk Size보다 작아야 합니다.")
            return

        ollama_model = self.ollama_model_input.text().strip()
        embedding_model = self.embedding_model_input.text().strip()
        chroma_dir = Path(self.chroma_path_input.text()).expanduser()
        ocr_enabled = self.ocr_checkbox.isChecked()

        update_runtime_config(ollama_model, embedding_model, chunk_size, chunk_overlap, chroma_dir, ocr_enabled)
        env_path = save_env_config(ollama_model, embedding_model, chunk_size, chunk_overlap, chroma_dir, ocr_enabled)
        QMessageBox.information(self, "설정 저장", f"설정을 저장했습니다.\n.env 위치: {env_path}")
