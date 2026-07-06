"""TXT 문서 로더를 제공합니다."""

from __future__ import annotations

from pathlib import Path

from src.utils.exceptions import DocumentLoadError
from src.utils.file_utils import write_processed_text


class TxtLoader:
    """TXT 파일에서 텍스트를 읽는 로더입니다."""

    def load(self, file_path: str | Path) -> str:
        """TXT 파일을 UTF-8, cp949, euc-kr 순서로 읽어 텍스트를 반환합니다."""
        path = Path(file_path).expanduser()
        if not path.exists():
            raise DocumentLoadError(f"TXT 파일을 찾을 수 없습니다: {path}")
        if path.suffix.lower() != ".txt":
            raise DocumentLoadError(f"TXT 파일만 읽을 수 있습니다: {path}")

        errors: list[str] = []
        for encoding in ("utf-8", "cp949", "euc-kr"):
            try:
                # 한국어 Windows 문서까지 처리하기 위해 인코딩을 순서대로 재시도합니다.
                text = path.read_text(encoding=encoding).strip()
                write_processed_text(path, text)
                return text
            except UnicodeDecodeError as exc:
                errors.append(f"{encoding}: {exc}")
            except Exception as exc:
                raise DocumentLoadError(f"TXT 파일 읽기에 실패했습니다: {path}") from exc

        error_detail = " / ".join(errors)
        raise DocumentLoadError(
            f"TXT 인코딩을 읽을 수 없습니다: {path}\n"
            f"시도한 인코딩: utf-8, cp949, euc-kr\n"
            f"상세 오류: {error_detail}"
        )
