"""소스코드 파일 지원 기능을 검증합니다."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from src.loader.code_loader import CodeLoader
from src.loader.dispatcher import DocumentDispatcher
from src.models import Document
from src.preprocess.code_chunker import CodeChunker
from src.rag.document_indexer import DocumentIndexer
from src.rag.retriever import Retriever


class CodeLoaderTest(TestCase):
    """코드 로더와 메타데이터 생성 테스트입니다."""

    def test_load_python_code_with_metadata(self) -> None:
        """Python 코드 파일을 읽고 코드 메타데이터를 생성합니다."""
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "example.py"
            path.write_text("def hello():\n    return 'hi'\n", encoding="utf-8")

            loader = CodeLoader()
            text = loader.load(path)
            metadata = loader.metadata(path)

            self.assertIn("def hello", text)
            self.assertEqual(metadata["language"], "Python")
            self.assertEqual(metadata["extension"], ".py")
            self.assertEqual(metadata["source_type"], "code")
            self.assertEqual(metadata["file"], "example.py")

    def test_dispatcher_wraps_code_as_document(self) -> None:
        """확장자 분기에서 코드 파일이 Document로 변환됩니다."""
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.c"
            path.write_text("int main(void) { return 0; }\n", encoding="utf-8")

            documents = DocumentDispatcher().load(path)

            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0].document_type, "code")
            self.assertEqual(documents[0].metadata["language"], "C")
            self.assertEqual(documents[0].metadata["source_type"], "code")


class CodeCollectAndChunkTest(TestCase):
    """코드 파일 수집과 코드 Chunk 분리 테스트입니다."""

    def test_collect_supported_files_reads_code_in_nested_folders(self) -> None:
        """지정 폴더의 하위 폴더까지 코드 파일을 재귀적으로 찾습니다."""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "src" / "main"
            nested.mkdir(parents=True)
            java_path = nested / "Main.java"
            py_path = root / "solve.py"
            ignored_path = nested / "README.md"
            java_path.write_text("class Main {}\n", encoding="utf-8")
            py_path.write_text("print('ok')\n", encoding="utf-8")
            ignored_path.write_text("ignore", encoding="utf-8")

            files = DocumentIndexer().collect_supported_files([root])

            self.assertCountEqual(files, [java_path.resolve(), py_path.resolve()])

    def test_code_chunker_keeps_code_metadata(self) -> None:
        """코드 Chunk에 언어와 source_type 메타데이터가 유지됩니다."""
        document = Document(
            source_path=Path("sample.py"),
            text="class Solver:\n    pass\n\ndef solve():\n    return 1\n",
            document_type="code",
            metadata={"language": "Python", "source_type": "code", "extension": ".py", "file": "sample.py"},
        )

        chunks = CodeChunker(chunk_size=80).split(document)

        self.assertGreaterEqual(len(chunks), 1)
        self.assertTrue(all(chunk.metadata["source_type"] == "code" for chunk in chunks))
        self.assertTrue(all(chunk.metadata["language"] == "Python" for chunk in chunks))
        self.assertTrue(all(chunk.metadata["chunk_strategy"] == "code" for chunk in chunks))


class RetrieverCodeFilterTest(TestCase):
    """질문 기반 코드 우선 검색 필터 테스트입니다."""

    def test_builds_language_specific_code_filter(self) -> None:
        """C 언어 질문은 C 코드 필터를 생성합니다."""
        retriever = Retriever()

        metadata_filter = retriever._build_preferred_filter("C 포인터 문제를 설명해줘")

        self.assertEqual(metadata_filter, {"$and": [{"source_type": "code"}, {"language": "C"}]})

    def test_builds_code_filter_for_code_keyword(self) -> None:
        """언어명이 없어도 코드 관련 질문이면 코드 우선 필터를 생성합니다."""
        retriever = Retriever()

        metadata_filter = retriever._build_preferred_filter("반복문 코드 출력 결과 알려줘")

        self.assertEqual(metadata_filter, {"source_type": "code"})
