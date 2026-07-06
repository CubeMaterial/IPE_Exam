"""PySide6 백그라운드 작업 Worker를 제공합니다."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot


class Worker(QObject):
    """오래 걸리는 작업을 UI 메인 스레드 밖에서 실행하는 Worker입니다."""

    progress = Signal(int)
    log = Signal(str)
    result = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, task: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """실행할 작업과 인자를 초기화합니다."""
        super().__init__()
        self.task = task
        self.args = args
        self.kwargs = kwargs

    @Slot()
    def run(self) -> None:
        """작업을 실행하고 결과 또는 오류 Signal을 발생시킵니다."""
        try:
            # 작업 함수가 progress/log 콜백을 받을 수 있도록 신호 emit 함수를 주입합니다.
            self.kwargs.setdefault("progress_callback", self.progress.emit)
            self.kwargs.setdefault("log_callback", self.log.emit)
            output = self.task(*self.args, **self.kwargs)
            self.result.emit(output)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            self.finished.emit()
