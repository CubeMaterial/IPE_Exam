"""Concept Dictionary 편집 탭을 제공합니다."""

from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.analyzer.concept_dictionary import ConceptDictionary


class ConceptDictionaryTab(QWidget):
    """개념 사전 JSON을 GUI에서 수정합니다."""

    def __init__(self, dictionary: ConceptDictionary | None = None) -> None:
        """탭 UI를 초기화합니다."""
        super().__init__()
        self.dictionary = dictionary or ConceptDictionary()
        self._build_ui()
        self._load_selected()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.file_combo = QComboBox()
        self.reload_button = QPushButton("다시 불러오기")
        self.save_button = QPushButton("저장")
        self.reload_button.clicked.connect(self._load_selected)
        self.save_button.clicked.connect(self._save_selected)
        self.file_combo.currentTextChanged.connect(self._load_selected)
        controls.addWidget(self.file_combo)
        controls.addWidget(self.reload_button)
        controls.addWidget(self.save_button)
        self.editor = QTextEdit()
        self.editor.setPlaceholderText('예: {\n  "MERGE": ["merge"]\n}')
        layout.addLayout(controls)
        layout.addWidget(self.editor)
        self._refresh_files()

    def _refresh_files(self) -> None:
        self.file_combo.blockSignals(True)
        self.file_combo.clear()
        self.file_combo.addItems(self.dictionary.filenames())
        self.file_combo.blockSignals(False)

    def _load_selected(self) -> None:
        filename = self.file_combo.currentText()
        if not filename:
            self.editor.setPlainText("")
            return
        data = self.dictionary._read_file(self.dictionary.directory / filename)
        self.editor.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))

    def _save_selected(self) -> None:
        filename = self.file_combo.currentText()
        if not filename:
            return
        try:
            data = json.loads(self.editor.toPlainText())
        except json.JSONDecodeError as exc:
            QMessageBox.critical(self, "Concept Dictionary", f"JSON 형식 오류: {exc}")
            return
        if not isinstance(data, dict) or any(not isinstance(value, list) for value in data.values()):
            QMessageBox.warning(self, "Concept Dictionary", "형식은 {개념: [키워드, ...]} 이어야 합니다.")
            return
        path = self.dictionary.save(filename, data)
        QMessageBox.information(self, "Concept Dictionary", f"저장 완료: {path}")
