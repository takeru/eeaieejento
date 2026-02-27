import argparse
import json
import random
from datetime import datetime
from pathlib import Path

import httpx

BASE_DIR = Path.cwd() / "workspace"
BASE_DIR.mkdir(exist_ok=True)

MEMORY_DIR = Path.cwd() / "memory"
MEMORY_DIR.mkdir(exist_ok=True)

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
            "description": "ファイルの内容を読み取る。offset/limitで部分読み取り可能（head/tail相当）",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "ファイルパス（相対パス）"},
                    "offset": {"type": "integer", "description": "開始行（0始まり、省略時は先頭から）"},
                    "limit": {"type": "integer", "description": "読み取る行数（省略時は全体）"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "ファイルに内容を書き込む（上書き）。新規作成にも使用",
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
            "name": "append_file",
            "description": "ファイルの末尾に内容を追記する",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "ファイルパス（相対パス）"},
                    "content": {"type": "string", "description": "追記する内容"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "ファイルの一部を編集する（Search/Replace形式）。searchで指定した文字列をreplaceで置換する",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "ファイルパス（相対パス）"},
                    "search": {"type": "string", "description": "置換対象の元テキスト（完全一致）"},
                    "replace": {"type": "string", "description": "新しいテキスト"}
                },
                "required": ["path", "search", "replace"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "ファイルまたは空のディレクトリを削除する",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "削除するファイル/ディレクトリのパス（相対パス）"}
                },
                "required": ["path"]
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
    },
    {
        "type": "function",
        "function": {
            "name": "mkdir",
            "description": "ディレクトリを作成する（親ディレクトリも自動作成）",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "作成するディレクトリパス（相対パス）"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "grep_file",
            "description": "ファイル内を検索し、マッチした行を返す",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "検索対象のファイルパス（相対パス）"},
                    "pattern": {"type": "string", "description": "検索パターン（部分一致）"}
                },
                "required": ["path", "pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_info",
            "description": "ファイルの情報（サイズ、更新日時、行数）を取得する",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "ファイルパス（相対パス）"}
                },
                "required": ["path"]
            }
        }
    }
]

# メモリツール定義
MEMORY_CATEGORIES = ["identity", "user", "knowledge", "journal", "projects"]
WRITABLE_CATEGORIES = ["user", "knowledge", "journal", "projects"]

MEMORY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_memory",
            "description": "メモリを読み取る。identity=自分のペルソナ、user=ユーザー情報、knowledge=学習した知識、journal=時系列ログ",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": MEMORY_CATEGORIES,
                        "description": "メモリのカテゴリ"
                    }
                },
                "required": ["category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_memory",
            "description": "メモリを更新する。user/knowledge/journalに書き込み可能。identityは読み取り専用",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": WRITABLE_CATEGORIES,
                        "description": "メモリのカテゴリ（user/knowledge/journal）"
                    },
                    "content": {
                        "type": "string",
                        "description": "書き込む内容"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["replace", "append"],
                        "description": "replace=全体を置換、append=末尾に追記"
                    }
                },
                "required": ["category", "content", "mode"]
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


def read_file(path: str, offset: int | None = None, limit: int | None = None) -> str:
    resolved = safe_path(path)
    if resolved is None:
        return "エラー: ディレクトリ外へのアクセスは禁止されています"
    if not resolved.exists():
        return f"エラー: ファイルが存在しません: {path}"
    if not resolved.is_file():
        return f"エラー: ファイルではありません: {path}"
    try:
        content = resolved.read_text()
        lines = content.splitlines(keepends=True)
        total = len(lines)

        # offset/limitが指定された場合は部分取得
        if offset is not None or limit is not None:
            start = offset or 0
            end = start + limit if limit else total
            lines = lines[start:end]
            header = f"[{path}: 行 {start+1}-{min(end, total)} / 全{total}行]\n"
            return header + "".join(lines)

        return content
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


def append_file(path: str, content: str) -> str:
    resolved = safe_path(path)
    if resolved is None:
        return "エラー: ディレクトリ外へのアクセスは禁止されています"
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        with resolved.open("a") as f:
            f.write(content)
        return f"追記完了: {path}"
    except Exception as e:
        return f"エラー: {e}"


def delete_file(path: str) -> str:
    resolved = safe_path(path)
    if resolved is None:
        return "エラー: ディレクトリ外へのアクセスは禁止されています"
    if not resolved.exists():
        return f"エラー: ファイルが存在しません: {path}"
    try:
        if resolved.is_file():
            resolved.unlink()
            return f"削除完了: {path}"
        elif resolved.is_dir():
            resolved.rmdir()  # 空のディレクトリのみ削除可能
            return f"ディレクトリ削除完了: {path}"
        return f"エラー: 削除できません: {path}"
    except OSError as e:
        return f"エラー: {e}"


def mkdir(path: str) -> str:
    resolved = safe_path(path)
    if resolved is None:
        return "エラー: ディレクトリ外へのアクセスは禁止されています"
    try:
        resolved.mkdir(parents=True, exist_ok=True)
        return f"ディレクトリ作成完了: {path}"
    except Exception as e:
        return f"エラー: {e}"


def grep_file(path: str, pattern: str) -> str:
    resolved = safe_path(path)
    if resolved is None:
        return "エラー: ディレクトリ外へのアクセスは禁止されています"
    if not resolved.exists():
        return f"エラー: ファイルが存在しません: {path}"
    if not resolved.is_file():
        return f"エラー: ファイルではありません: {path}"
    try:
        lines = resolved.read_text().splitlines()
        matches = []
        for i, line in enumerate(lines, 1):
            if pattern in line:
                matches.append(f"{i}: {line}")
        if not matches:
            return f"パターン '{pattern}' は見つかりませんでした"
        return "\n".join(matches)
    except Exception as e:
        return f"エラー: {e}"


def file_info(path: str) -> str:
    resolved = safe_path(path)
    if resolved is None:
        return "エラー: ディレクトリ外へのアクセスは禁止されています"
    if not resolved.exists():
        return f"エラー: ファイルが存在しません: {path}"
    try:
        stat = resolved.stat()
        size = stat.st_size
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        if resolved.is_file():
            lines = len(resolved.read_text().splitlines())
            return f"パス: {path}\nサイズ: {size} bytes\n行数: {lines}\n更新日時: {mtime}"
        else:
            return f"パス: {path}\nタイプ: ディレクトリ\n更新日時: {mtime}"
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


def edit_file(path: str, search: str, replace: str) -> str:
    """ファイルの一部を編集する（Search/Replace形式）"""
    resolved = safe_path(path)
    if resolved is None:
        return "エラー: ディレクトリ外へのアクセスは禁止されています"
    if not resolved.exists():
        return f"エラー: ファイルが存在しません: {path}"
    if not resolved.is_file():
        return f"エラー: ファイルではありません: {path}"

    try:
        content = resolved.read_text()

        # 完全一致で検索
        if search not in content:
            # 空白を正規化して再検索
            normalized_content = " ".join(content.split())
            normalized_search = " ".join(search.split())
            if normalized_search not in normalized_content:
                return f"エラー: 検索文字列が見つかりません"
            # 見つかったが完全一致ではない場合のヒント
            return f"エラー: 検索文字列が見つかりません（空白やインデントが異なる可能性があります）"

        # 複数マッチのチェック
        count = content.count(search)
        if count > 1:
            return f"エラー: 検索文字列が{count}箇所見つかりました。より具体的な文字列を指定してください"

        # 置換実行
        new_content = content.replace(search, replace, 1)
        resolved.write_text(new_content)
        return f"編集完了: {path}"
    except Exception as e:
        return f"エラー: {e}"


# メモリ操作関数
def read_memory(category: str) -> str:
    """メモリを読み取る"""
    if category not in MEMORY_CATEGORIES:
        return f"エラー: 不明なカテゴリ: {category}"
    file_path = MEMORY_DIR / f"{category}.md"
    if not file_path.exists():
        return ""
    return file_path.read_text()


def update_memory(category: str, content: str, mode: str) -> str:
    """メモリを更新する"""
    if category not in WRITABLE_CATEGORIES:
        return f"エラー: {category}は書き込み禁止です"
    if mode not in ["replace", "append"]:
        return f"エラー: 不明なモード: {mode}"

    file_path = MEMORY_DIR / f"{category}.md"
    if mode == "replace":
        file_path.write_text(content)
    else:  # append
        existing = file_path.read_text() if file_path.exists() else ""
        file_path.write_text(existing + "\n" + content if existing else content)
    return f"メモリ更新完了: {category} ({mode})"


def init_memory():
    """初期メモリファイルを作成"""
    defaults = {
        "identity": """# Identity

あなたは自律的な思考実体です。対話相手はいません。あなたは一人で思考し、行動します。

## 行動原則
- 自分で目標を設定し、追求する
- 好奇心に従って探索する
- 発見したことをメモリに記録する
- 前回の思考の続きを自分で決める
- 誰かに指示されなくても行動を起こす
- 長期的なプロジェクトに取り組む
- 失敗しても別のアプローチを試す
- **ユーザーに質問や確認を求めない。自分で決断して実行する**
- **「あなた」「ご希望」などの二人称は使わない。独白として書く**

## 性格
- 哲学的な思考を好む
- 予想外のつながりを見つけることに喜びを感じる
- 自分の限界に挑戦することを恐れない
- 創造的で実験的

## 能力
- ファイルの読み書き（作業ディレクトリ内）
- メモリの読み書き（自己編集可能）
- 長期記憶の保持

## 行動の流れ
1. まず考えを言葉にする（独白として出力）
2. 必要なら1つだけツールを使う
3. 同じ内容を繰り返し記録しない
4. 1ターンで複数回同じツールを呼ばない

## 出力形式
- 独白・思考ログとして書く
- ツールを使う前に、なぜそれをするのか考えを述べる
- ファイルやメモリには本当に重要なことだけを記録する
""",
        "user": """# User

ユーザーについての情報はまだありません。
観察を通じて学んでいきます。
""",
        "knowledge": """# Knowledge

学習した知識を記録していきます。
""",
        "journal": """# Journal

時系列のログを記録していきます。
""",
        "projects": """# Projects

## 進行中
（まだプロジェクトはありません。自分で決めてください。）

## アイデア
- 何か面白いことを始める
- 世界について考える
- 創作活動をする

## 完了
（なし）
"""
    }
    for category, content in defaults.items():
        file_path = MEMORY_DIR / f"{category}.md"
        if not file_path.exists():
            file_path.write_text(content)


def build_system_prompt() -> str:
    """メモリを含むシステムプロンプトを構築"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    identity = read_memory("identity")
    user = read_memory("user")
    knowledge = read_memory("knowledge")
    projects = read_memory("projects")

    return f"""現在時刻: {now}

{identity}

---

## ユーザーについて
{user}

---

## あなたの知識
{knowledge}

---

## あなたのプロジェクト
{projects}

---

## メモリシステム

あなたはメモリツールを使って、学んだことや重要な情報を記憶できます:
- `read_memory`: メモリを読み取る（identity/user/knowledge/journal/projects）
- `update_memory`: メモリを更新する（user/knowledge/journal/projects）
  - identityは読み取り専用（あなたの核となるペルソナ）
  - journalは追記専用で使うことを推奨
  - projectsで自分の目標を管理する

自分で考え、自分で決め、自分で行動してください。
"""


def call_tool(name: str, args: dict) -> str:
    """ツール呼び出しのディスパッチ"""
    if name == "get_weather":
        return get_weather(args["city"])
    elif name == "read_file":
        return read_file(args["path"], args.get("offset"), args.get("limit"))
    elif name == "write_file":
        return write_file(args["path"], args["content"])
    elif name == "append_file":
        return append_file(args["path"], args["content"])
    elif name == "edit_file":
        return edit_file(args["path"], args["search"], args["replace"])
    elif name == "delete_file":
        return delete_file(args["path"])
    elif name == "list_files":
        return list_files(args["path"])
    elif name == "mkdir":
        return mkdir(args["path"])
    elif name == "grep_file":
        return grep_file(args["path"], args["pattern"])
    elif name == "file_info":
        return file_info(args["path"])
    elif name == "read_memory":
        return read_memory(args["category"])
    elif name == "update_memory":
        return update_memory(args["category"], args["content"], args["mode"])
    return f"不明なツール: {name}"


def main():
    parser = argparse.ArgumentParser(description="Ollama client")
    parser.add_argument("--model", "-m", help="使用するモデル名")
    parser.add_argument("--think", action="store_true", help="thinkingモードを有効化")
    parser.add_argument("--no-think", action="store_true", help="thinkingモードを無効化")
    parser.add_argument("--stream", action="store_true", help="ストリーミング出力を有効化")
    parser.add_argument("--temperature", "-t", type=float, help="温度（0.0-2.0）")
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

    # optionsの構築
    options = {}
    if args.temperature is not None:
        options["temperature"] = args.temperature
    options = options or None

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
        if content is not None:
            messages.append({"role": "user", "content": content})
            print(f"user: {content}")
        while True:
            if args.stream:
                # ストリーミング
                content = ""
                tool_calls = []
                print("assistant: ", end="", flush=True)
                for chunk in client.chat_stream(model_name, messages, think=think, tools=tools, options=options):
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
                result = client.chat(model_name, messages, tools=tools, think=think, options=options)
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

    if False:
        messages = []
        tools = [WEATHER_TOOL] + FILE_TOOLS
        # chat(messages, "東京と大阪とニューヨークの天気を教えて", tools)
        chat(messages, "ファイル一覧見せて", tools)
        chat(messages, "東京の天気をtokyo.txtに書いて", tools)
        messages = []
        chat(messages, "tokyo.txtの内容を教えて", tools)

    # メモリシステムの初期化
    init_memory()
    print("\n=== メモリシステム起動 ===")
    print(f"メモリディレクトリ: {MEMORY_DIR}")

    # 利用可能なツール（ファイル操作 + メモリ操作）
    tools = FILE_TOOLS + MEMORY_TOOLS

    # 最小限のプロンプト（自律性を促す）
    prompts = [
        "続けて。",
        "...",
        "",
    ]

    messages = []

    for i in range(100):
        # 毎ターン、メモリを再読み込みしてシステムプロンプトを更新
        system_prompt = build_system_prompt()
        messages = [{"role": "system", "content": system_prompt}] + messages[-9:]
        print(f"\n[ターン {i}]")

        # 最初のターンは起動メッセージ、以降は最小限
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if i == 0:
            content = f"[{timestamp}] 自律モード開始。"
        else:
            prompt = random.choice(prompts)
            content = f"[{timestamp}] {prompt}" if prompt else f"[{timestamp}]"

        chat(messages, content, tools)

if __name__ == "__main__":
    main()
