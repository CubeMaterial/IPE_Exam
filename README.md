# StudyRAG

Python 로컬 실행 기반 AI RAG 학습 도우미입니다.

## 실행 준비

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
ollama pull qwen3:8b
ollama pull nomic-embed-text
python main.py
```

`python main.py`를 실행하면 PySide6 기반 로컬 데스크톱 GUI가 열립니다.

## 주요 기능

- PDF/TXT/Markdown/이미지/ZIP 문서 등록
- EasyOCR 기반 이미지 및 스캔 PDF OCR
- Chunk 분리, Ollama 임베딩, ChromaDB 저장
- RAG 질문 답변 및 참고 문서/Chunk 출력
- 개념 분석, 문제 유형 분석, 예상문제 생성, 요약, 암기 카드 생성
