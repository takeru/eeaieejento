import json

import httpx

OLLAMA_BASE_URL = "http://localhost:11434"


class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self.client = httpx.Client(timeout=httpx.Timeout(10.0, read=600.0))

    def list_models(self) -> list[dict]:
        """利用可能なモデル一覧を取得"""
        response = self.client.get(f"{self.base_url}/api/tags")
        response.raise_for_status()
        return response.json().get("models", [])

    def generate(
        self, model: str, prompt: str, stream: bool = False, think: bool | None = None
    ) -> str:
        """テキスト生成（単発プロンプト）"""
        payload = {"model": model, "prompt": prompt, "stream": stream}
        if think is not None:
            payload["think"] = think
        response = self.client.post(f"{self.base_url}/api/generate", json=payload)
        response.raise_for_status()
        return response.json()["response"]

    def generate_stream(
        self, model: str, prompt: str, think: bool | None = None
    ):
        """テキスト生成（ストリーミング）"""
        payload = {"model": model, "prompt": prompt, "stream": True}
        if think is not None:
            payload["think"] = think
        with self.client.stream("POST", f"{self.base_url}/api/generate", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    yield json.loads(line)

    def chat(
        self,
        model: str,
        messages: list[dict],
        stream: bool = False,
        think: bool | None = None,
        tools: list[dict] | None = None,
        options: dict | None = None,
    ) -> dict:
        """チャット形式（会話履歴対応）"""
        payload = {"model": model, "messages": messages, "stream": stream}
        if think is not None:
            payload["think"] = think
        if tools is not None:
            payload["tools"] = tools
        if options is not None:
            payload["options"] = options
        response = self.client.post(f"{self.base_url}/api/chat", json=payload)
        response.raise_for_status()
        return response.json()

    def chat_stream(
        self,
        model: str,
        messages: list[dict],
        think: bool | None = None,
        tools: list[dict] | None = None,
        options: dict | None = None,
    ):
        """チャット形式（ストリーミング）"""
        payload = {"model": model, "messages": messages, "stream": True}
        if think is not None:
            payload["think"] = think
        if tools is not None:
            payload["tools"] = tools
        if options is not None:
            payload["options"] = options
        with self.client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    yield json.loads(line)
