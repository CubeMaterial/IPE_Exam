"""Rich 기반 CLI 메뉴를 제공합니다."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from config.config import ensure_directories
from src.analyzer.concept_analyzer import ConceptAnalyzer
from src.analyzer.question_analyzer import QuestionAnalyzer
from src.embedding.embedding import ChromaEmbeddingStore
from src.generator.expected_question_generator import ExpectedQuestionGenerator
from src.rag.document_indexer import DocumentIndexer
from src.rag.generator import RAGGenerator
from src.rag.retriever import Retriever
from src.utils.exceptions import StudyRAGError


class StudyRAGMenu:
    """StudyRAG CLI 메뉴와 사용자 입력 흐름을 담당합니다."""

    def __init__(self) -> None:
        """CLI에서 사용할 서비스 객체를 초기화합니다."""
        ensure_directories()
        self.console = Console()
        self.store = ChromaEmbeddingStore()
        self.retriever = Retriever(self.store)
        self.indexer = DocumentIndexer(store=self.store)
        self.rag_generator = RAGGenerator(retriever=self.retriever)
        self.concept_analyzer = ConceptAnalyzer(retriever=self.retriever)
        self.question_analyzer = QuestionAnalyzer()
        self.expected_generator = ExpectedQuestionGenerator()

    def run(self) -> None:
        """사용자가 종료할 때까지 메뉴를 실행합니다."""
        while True:
            self._render_menu()
            choice = Prompt.ask("메뉴 번호를 선택하세요", default="9")
            try:
                if choice == "1":
                    self._register_document()
                elif choice == "2":
                    self._ask_question()
                elif choice == "3":
                    self._analyze_concept()
                elif choice == "4":
                    self._analyze_question()
                elif choice == "5":
                    self._generate_expected_question()
                elif choice == "6":
                    self._summarize()
                elif choice == "7":
                    self._make_flashcards()
                elif choice == "8":
                    self._reset_db()
                elif choice == "9":
                    self.console.print("[bold green]StudyRAG를 종료합니다.[/bold green]")
                    break
                else:
                    self.console.print("[yellow]올바른 메뉴 번호를 입력하세요.[/yellow]")
            except StudyRAGError as exc:
                self.console.print(f"[bold red]오류:[/bold red] {exc}")
            except Exception as exc:
                self.console.print(f"[bold red]예상하지 못한 오류:[/bold red] {exc}")

    def _render_menu(self) -> None:
        """메인 메뉴를 화면에 출력합니다."""
        table = Table(show_header=False, box=None)
        table.add_column("번호", style="cyan", width=4)
        table.add_column("기능", style="white")
        for number, label in [
            ("1", "문서 등록"),
            ("2", "질문하기"),
            ("3", "개념 분석"),
            ("4", "문제 유형 분석"),
            ("5", "예상문제 생성"),
            ("6", "요약"),
            ("7", "암기 카드 생성"),
            ("8", "DB 초기화"),
            ("9", "종료"),
        ]:
            table.add_row(number, label)
        self.console.print(Panel(table, title="StudyRAG", border_style="blue"))

    def _register_document(self) -> None:
        """문서 파일을 등록합니다."""
        path = Prompt.ask("등록할 파일 경로를 입력하세요")
        count = self.indexer.index_file(path)
        self.console.print(f"[green]등록 완료:[/green] {count}개 Chunk가 저장되었습니다.")

    def _ask_question(self) -> None:
        """RAG 질문을 처리합니다."""
        question = Prompt.ask("질문을 입력하세요")
        answer = self.rag_generator.answer(question)
        self.console.print(Panel(answer, title="답변", border_style="green"))

    def _analyze_concept(self) -> None:
        """개념 분석 요청을 처리합니다."""
        concept = Prompt.ask("분석할 개념을 입력하세요")
        result = self.concept_analyzer.analyze(concept)
        self.console.print(Panel(result, title="개념 분석", border_style="green"))

    def _analyze_question(self) -> None:
        """기출문제 분석 요청을 처리합니다."""
        question_text = self._read_multiline("분석할 기출문제를 입력하세요")
        result = self.question_analyzer.analyze(question_text)
        self.console.print(Panel(result, title="문제 유형 분석", border_style="green"))

    def _generate_expected_question(self) -> None:
        """예상문제 생성 요청을 처리합니다."""
        question_type = Prompt.ask("문제 유형", default="객관식")
        source_text = self._read_multiline("기준 자료 또는 기출문제를 입력하세요")
        result = self.expected_generator.generate(source_text, question_type)
        self.console.print(Panel(result, title="예상문제", border_style="green"))

    def _summarize(self) -> None:
        """학습 자료 요약 요청을 처리합니다."""
        query = Prompt.ask("요약할 주제, 문서명, Chapter 또는 범위를 입력하세요")
        summary_type = Prompt.ask("요약 형식", default="시험용 암기 요약")
        result = self.rag_generator.summarize(query, summary_type)
        self.console.print(Panel(result, title="요약", border_style="green"))

    def _make_flashcards(self) -> None:
        """암기 카드 생성 요청을 처리합니다."""
        topic = Prompt.ask("암기 카드로 만들 개념 또는 주제를 입력하세요")
        result = self.rag_generator.make_flashcards(topic)
        self.console.print(Panel(result, title="암기 카드", border_style="green"))

    def _reset_db(self) -> None:
        """벡터DB를 초기화합니다."""
        confirm = Prompt.ask("정말 DB를 초기화할까요? yes/no", default="no")
        if confirm.lower() == "yes":
            self.store.reset()
            self.console.print("[green]DB가 초기화되었습니다.[/green]")
        else:
            self.console.print("[yellow]초기화를 취소했습니다.[/yellow]")

    def _read_multiline(self, title: str) -> str:
        """빈 줄이 입력될 때까지 여러 줄 텍스트를 읽습니다."""
        self.console.print(f"{title} [dim](입력을 마치려면 빈 줄 입력)[/dim]")
        lines: list[str] = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        return "\n".join(lines).strip()
