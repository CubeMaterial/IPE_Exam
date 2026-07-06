"""StudyRAG 메인 윈도우를 제공합니다."""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget

from config.config import ensure_directories
from src.ui.analyze_tab import ConceptAnalyzeTab, QuestionAnalyzeTab
from src.ui.chat_tab import ChatTab
from src.ui.document_tab import DocumentTab
from src.ui.flashcard_tab import FlashcardTab
from src.ui.generate_tab import GenerateTab
from src.ui.past_exam_tab import PastExamTab
from src.ui.settings_tab import SettingsTab
from src.ui.summary_tab import SummaryTab


class MainWindow(QMainWindow):
    """StudyRAG 데스크톱 앱의 메인 윈도우입니다."""

    def __init__(self) -> None:
        """메인 윈도우와 탭 UI를 초기화합니다."""
        super().__init__()
        ensure_directories()
        self.setWindowTitle("StudyRAG")
        self.resize(1100, 760)
        self._build_tabs()

    def _build_tabs(self) -> None:
        """요구사항에 맞는 기능 탭을 구성합니다."""
        tabs = QTabWidget()
        tabs.addTab(DocumentTab(), "문서 등록")
        tabs.addTab(ChatTab(), "질문하기")
        tabs.addTab(ConceptAnalyzeTab(), "개념 분석")
        tabs.addTab(QuestionAnalyzeTab(), "문제 유형 분석")
        tabs.addTab(GenerateTab(), "예상문제 생성")
        tabs.addTab(PastExamTab(), "과년도 기출 분석")
        tabs.addTab(SummaryTab(), "요약")
        tabs.addTab(FlashcardTab(), "암기 카드")
        tabs.addTab(SettingsTab(), "설정")
        self.setCentralWidget(tabs)
