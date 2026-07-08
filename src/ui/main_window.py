"""StudyRAG 메인 윈도우를 제공합니다."""

from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMessageBox, QMainWindow, QTabWidget

from config.config import ensure_directories
from src.ui.analyze_tab import ConceptAnalyzeTab, QuestionAnalyzeTab
from src.ui.chat_tab import ChatTab
from src.ui.concept_dictionary_tab import ConceptDictionaryTab
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
        tabs.addTab(ConceptDictionaryTab(), "Concept Dictionary")
        tabs.addTab(SummaryTab(), "요약")
        tabs.addTab(FlashcardTab(), "암기 카드")
        tabs.addTab(SettingsTab(), "설정")
        self.setCentralWidget(tabs)

    def closeEvent(self, event: QCloseEvent) -> None:
        """백그라운드 작업 중에는 창 종료를 막아 QThread abort를 방지합니다."""
        running_tabs = self._running_tab_names()
        if running_tabs:
            QMessageBox.warning(
                self,
                "작업 진행 중",
                "아직 처리 중인 작업이 있습니다.\n"
                f"완료 후 다시 종료하세요: {', '.join(running_tabs)}",
            )
            event.ignore()
            return
        super().closeEvent(event)

    def _running_tab_names(self) -> list[str]:
        """현재 실행 중인 QThread를 가진 탭 이름을 반환합니다."""
        tabs = self.centralWidget()
        if not isinstance(tabs, QTabWidget):
            return []

        running: list[str] = []
        for index in range(tabs.count()):
            widget = tabs.widget(index)
            thread = getattr(widget, "thread", None)
            if thread is not None and thread.isRunning():
                running.append(tabs.tabText(index))
        return running
