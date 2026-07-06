"""StudyRAG GUI 진입점입니다."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from src.ui.main_window import MainWindow


def main() -> None:
    """StudyRAG PySide6 데스크톱 애플리케이션을 실행합니다."""
    # GUI 진입점은 얇게 유지하고 실제 기능은 src 하위 서비스에 위임합니다.
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
