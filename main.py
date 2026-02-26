import argparse
import json

import httpx

OLLAMA_BASE_URL = "http://localhost:11434"


class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self.client = httpx.Client(timeout=120.0)

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
    ) -> dict:
        """チャット形式（会話履歴対応）"""
        payload = {"model": model, "messages": messages, "stream": stream}
        if think is not None:
            payload["think"] = think
        if tools is not None:
            payload["tools"] = tools
        response = self.client.post(f"{self.base_url}/api/chat", json=payload)
        response.raise_for_status()
        return response.json()

    def chat_stream(
        self,
        model: str,
        messages: list[dict],
        think: bool | None = None,
        tools: list[dict] | None = None,
    ):
        """チャット形式（ストリーミング）"""
        payload = {"model": model, "messages": messages, "stream": True}
        if think is not None:
            payload["think"] = think
        if tools is not None:
            payload["tools"] = tools
        with self.client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    yield json.loads(line)


# ツール定義
WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "指定した都市の天気を取得する",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "都市名（例: 東京、大阪、ニューヨーク）"
                }
            },
            "required": ["city"]
        }
    }
}


def get_weather(city: str) -> str:
    """天気を返すダミー関数"""
    weather_data = {
        "東京": "はれ",
        "大阪": "ぶた",
        "ニューヨーク": "ブリザード",
    }
    return weather_data.get(city, "不明")


def main():
    parser = argparse.ArgumentParser(description="Ollama client")
    parser.add_argument("--model", "-m", help="使用するモデル名")
    parser.add_argument("--think", action="store_true", help="thinkingモードを有効化")
    parser.add_argument("--no-think", action="store_true", help="thinkingモードを無効化")
    parser.add_argument("--stream", action="store_true", help="ストリーミング出力を有効化")
    args = parser.parse_args()

    client = OllamaClient()

    # モデル一覧を表示
    print("=== 利用可能なモデル ===")
    models = client.list_models()
    for m in models:
        print(f"  - {m['name']}")

    if args.model:
        model_name = args.model
    elif models:
        model_name = models[0]["name"]
    else:
        print("モデルがありません。ollama pull <model> でモデルをダウンロードしてください")
        return

    # thinkオプションの決定
    think = None
    if args.think:
        think = True
    elif args.no_think:
        think = False

    print(f"\n=== {model_name} でテスト生成 (think={think}, stream={args.stream}) ===")

    # generate API
    if args.stream:
        print("generate: ", end="", flush=True)
        for chunk in client.generate_stream(model_name, "こんにちは、自己紹介してください。", think=think):
            print(chunk.get("response", ""), end="", flush=True)
        print()
    else:
        response = client.generate(model_name, "こんにちは、自己紹介してください。", think=think)
        print(f"generate: {response}")

    # chat API
    print("\n=== chat APIテスト ===")
    if not args.stream:
        def chat(messages, content):
            messages.append({"role": "user", "content": content})
            print(f"user: {content}")
            result = client.chat(
                model_name,
                messages=messages,
                think=think,
            )
            if "thinking" in result.get("message", {}):
                print(f"thinking: {result['message']['thinking']}")
            print(f"assistant: {result['message']['content']}")
        messages = []
        chat(messages, "1+1は？")
        chat(messages, "さらに+4は？")
    else:
        def chat(messages, content):
            messages.append({"role": "user", "content": content})
            print(f"user: {content}")
            print("assistant: ", end="", flush=True)
            content = ""
            for chunk in client.chat_stream(model_name, messages, think=think):
                msg = chunk.get("message", {})
                if msg.get("content"):
                    print(msg["content"], end="", flush=True)
                    content += msg["content"]
            messages.append({"role": "assistant", "content": content})
            print()
        messages = []
        chat(messages, "1+1は？")
        chat(messages, "さらに+3は？")

    # tool useデモ
    print("\n=== tool useデモ ===")
    tools = [WEATHER_TOOL]
    messages = [{"role": "user", "content": "東京と大阪とニューヨークの天気を教えて"}]
    print(f"user: {messages[0]['content']}")

    while True:
        if args.stream:
            # ストリーミング
            content = ""
            tool_calls = []
            print("assistant: ", end="", flush=True)
            for chunk in client.chat_stream(model_name, messages, think=think, tools=tools):
                msg = chunk.get("message", {})
                if msg.get("content"):
                    print(msg["content"], end="", flush=True)
                    content += msg["content"]
                if msg.get("tool_calls"):
                    tool_calls.extend(msg["tool_calls"])
            print()
            msg = {"role": "assistant", "content": content}
            if tool_calls:
                msg["tool_calls"] = tool_calls
        else:
            # 非ストリーミング
            result = client.chat(model_name, messages, tools=tools, think=think)
            msg = result["message"]

        messages.append(msg)

        # tool_callsがあれば実行
        if msg.get("tool_calls"):
            for tool_call in msg["tool_calls"]:
                func = tool_call["function"]
                print(f"[tool call] {func['name']}({func['arguments']})")

                if func["name"] == "get_weather":
                    tool_result = get_weather(func["arguments"]["city"])
                    print(f"[tool result] {tool_result}")
                    messages.append({
                        "role": "tool",
                        "content": tool_result,
                    })
        else:
            # tool呼び出しがなければ最終応答
            if not args.stream:
                print(f"assistant: {msg['content']}")
            break


if __name__ == "__main__":
    main()
