import argparse
import json
from pathlib import Path

import httpx

BASE_DIR = Path.cwd()

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


# ファイル操作ツール
FILE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "ファイルの内容を読み取る",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "ファイルパス（相対パス）"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "ファイルに内容を書き込む（上書き）",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "ファイルパス（相対パス）"},
                    "content": {"type": "string", "description": "書き込む内容"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "ディレクトリ内のファイル一覧を取得",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "ディレクトリパス（相対パス）"}
                },
                "required": ["path"]
            }
        }
    }
]


def safe_path(path: str) -> Path | None:
    """パスを検証し、BASE_DIR内であれば絶対パスを返す。外部なら None"""
    try:
        resolved = (BASE_DIR / path).resolve()
        if BASE_DIR in resolved.parents or resolved == BASE_DIR:
            return resolved
        return None
    except Exception:
        return None


def read_file(path: str) -> str:
    resolved = safe_path(path)
    if resolved is None:
        return "エラー: ディレクトリ外へのアクセスは禁止されています"
    if not resolved.exists():
        return f"エラー: ファイルが存在しません: {path}"
    if not resolved.is_file():
        return f"エラー: ファイルではありません: {path}"
    try:
        return resolved.read_text()
    except Exception as e:
        return f"エラー: {e}"


def write_file(path: str, content: str) -> str:
    resolved = safe_path(path)
    if resolved is None:
        return "エラー: ディレクトリ外へのアクセスは禁止されています"
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content)
        return f"書き込み完了: {path}"
    except Exception as e:
        return f"エラー: {e}"


def list_files(path: str) -> str:
    resolved = safe_path(path)
    if resolved is None:
        return "エラー: ディレクトリ外へのアクセスは禁止されています"
    if not resolved.exists():
        return f"エラー: ディレクトリが存在しません: {path}"
    if not resolved.is_dir():
        return f"エラー: ディレクトリではありません: {path}"
    try:
        files = sorted(resolved.iterdir())
        return "\n".join(f.name + ("/" if f.is_dir() else "") for f in files)
    except Exception as e:
        return f"エラー: {e}"


def call_tool(name: str, args: dict) -> str:
    """ツール呼び出しのディスパッチ"""
    if name == "get_weather":
        return get_weather(args["city"])
    elif name == "read_file":
        return read_file(args["path"])
    elif name == "write_file":
        return write_file(args["path"], args["content"])
    elif name == "list_files":
        return list_files(args["path"])
    return f"不明なツール: {name}"


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
    if False:
        if args.stream:
            print("generate: ", end="", flush=True)
            for chunk in client.generate_stream(model_name, "こんにちは、自己紹介してください。", think=think):
                print(chunk.get("response", ""), end="", flush=True)
            print()
        else:
            response = client.generate(model_name, "こんにちは、自己紹介してください。", think=think)
            print(f"generate: {response}")

    # chat API
    if False:
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
    def chat(messages, content, tools):
        messages.append({"role": "user", "content": content})
        print(f"user: {content}")
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
                    tool_result = call_tool(func["name"], func["arguments"])
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

    messages = []
    tools = [WEATHER_TOOL] + FILE_TOOLS
    # chat(messages, "東京と大阪とニューヨークの天気を教えて", tools)
    chat(messages, "ファイル一覧見せて", tools)
    chat(messages, "東京の天気をtokyo.txtに書いて", tools)
    messages = []
    chat(messages, "tokyo.txtの内容を教えて", tools)


if __name__ == "__main__":
    main()
