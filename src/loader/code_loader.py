"""소스코드 파일 로더를 제공합니다."""

from __future__ import annotations

from pathlib import Path

from src.utils.code_utils import detect_language_by_extension, is_code_file
from src.utils.exceptions import DocumentLoadError
from src.utils.file_utils import write_processed_text


class CodeLoader:
    """지원하는 소스코드 파일에서 텍스트를 읽는 로더입니다."""

    def load(self, file_path: str | Path) -> str:
        """코드 파일을 UTF-8, cp949, euc-kr 순서로 읽어 텍스트를 반환합니다."""
        path = Path(file_path).expanduser()
        if not path.exists():
            raise DocumentLoadError(f"코드 파일을 찾을 수 없습니다: {path}")
        if not is_code_file(path):
            raise DocumentLoadError(f"지원하지 않는 코드 파일 형식입니다: {path.suffix}")

        errors: list[str] = []
        for encoding in ("utf-8", "cp949", "euc-kr"):
            try:
                # 국내 학습 자료의 Windows 인코딩까지 처리하기 위해 순서대로 재시도합니다.
                text = path.read_text(encoding=encoding)
                write_processed_text(path, text, suffix=".code.txt")
                return text
            except UnicodeDecodeError as exc:
                errors.append(f"{encoding}: {exc}")
            except Exception as exc:
                raise DocumentLoadError(f"코드 파일 읽기에 실패했습니다: {path}") from exc

        error_detail = " / ".join(errors)
        raise DocumentLoadError(
            f"코드 파일 인코딩을 읽을 수 없습니다: {path}\n"
            f"시도한 인코딩: utf-8, cp949, euc-kr\n"
            f"상세 오류: {error_detail}"
        )

    def metadata(self, file_path: str | Path) -> dict[str, str]:
        """코드 파일 저장에 필요한 메타데이터를 생성합니다."""
        path = Path(file_path).expanduser()
        language = detect_language_by_extension(path)
        return {
            "language": language,
            "file_name": path.name,
            "file": path.name,
            "extension": path.suffix.lower(),
            "source_type": "code",
        }
