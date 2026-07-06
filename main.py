"""StudyRAG CLI 진입점입니다."""

from __future__ import annotations

from src.ui.menu import StudyRAGMenu


def main() -> None:
    """StudyRAG 애플리케이션을 실행합니다."""
    # UI 진입점은 얇게 유지하고 실제 기능은 src 하위 서비스에 위임합니다.
    StudyRAGMenu().run()


if __name__ == "__main__":
    main()
