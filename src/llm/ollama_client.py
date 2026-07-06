"""Ollama API 클라이언트를 제공합니다."""

from __future__ import annotations

import json
from typing import Any
from urllib import request
from urllib.error import URLError

from config.config import CONFIG
from src.utils.exceptions import LLMError


class OllamaClient:
    """Ollama 로컬 서버와 통신하는 클라이언트입니다."""

    def __init__(
        self,
        base_url: str = CONFIG.ollama_base_url,
        model: str = CONFIG.ollama_model,
        embedding_model: str = CONFIG.embedding_model,
    ) -> None:
        """Ollama 서버 URL과 모델명을 초기화합니다."""
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embedding_model = embedding_model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Ollama chat API를 호출해 답변을 생성합니다."""
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        response = self._post_json("/api/chat", payload)
        message = response.get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise LLMError("Ollama 응답에서 content를 찾을 수 없습니다.")
        return content.strip()

    def embed(self, text: str) -> list[float]:
        """Ollama embedding API를 호출해 텍스트 임베딩을 생성합니다."""
        payload = {"model": self.embedding_model, "prompt": text}
        response = self._post_json("/api/embeddings", payload)
        embedding = response.get("embedding")
        if not isinstance(embedding, list):
            raise LLMError("Ollama 응답에서 embedding을 찾을 수 없습니다.")
        return [float(value) for value in embedding]

    def _post_json(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        """JSON 요청을 전송하고 JSON 응답을 반환합니다."""
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{endpoint}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))
        except URLError as exc:
            raise LLMError("Ollama 서버에 연결할 수 없습니다. ollama serve 상태를 확인하세요.") from exc
        except json.JSONDecodeError as exc:
            raise LLMError("Ollama 응답 JSON을 해석할 수 없습니다.") from exc
