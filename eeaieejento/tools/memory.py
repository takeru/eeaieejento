from datetime import datetime
from pathlib import Path

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


def read_memory(category: str, memory_dir: Path) -> str:
    """メモリを読み取る"""
    if category not in MEMORY_CATEGORIES:
        return f"エラー: 不明なカテゴリ: {category}"
    file_path = memory_dir / f"{category}.md"
    if not file_path.exists():
        return ""
    return file_path.read_text()


def update_memory(category: str, content: str, mode: str, memory_dir: Path) -> str:
    """メモリを更新する"""
    if category not in WRITABLE_CATEGORIES:
        return f"エラー: {category}は書き込み禁止です"
    if mode not in ["replace", "append"]:
        return f"エラー: 不明なモード: {mode}"
    file_path = memory_dir / f"{category}.md"
    if mode == "replace":
        file_path.write_text(content)
    else:
        existing = file_path.read_text() if file_path.exists() else ""
        file_path.write_text(existing + "\n" + content if existing else content)
    return f"メモリ更新完了: {category} ({mode})"


DEFAULT_IDENTITY = """# Identity

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
"""

DEFAULT_MEMORY = {
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


def init_memory(memory_dir: Path):
    """初期メモリファイルを作成"""
    memory_dir.mkdir(parents=True, exist_ok=True)
    defaults = {"identity": DEFAULT_IDENTITY, **DEFAULT_MEMORY}
    for category, content in defaults.items():
        file_path = memory_dir / f"{category}.md"
        if not file_path.exists():
            file_path.write_text(content)


def build_system_prompt(memory_dir: Path) -> str:
    """メモリを含むシステムプロンプトを構築"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    identity = read_memory("identity", memory_dir)
    user = read_memory("user", memory_dir)
    knowledge = read_memory("knowledge", memory_dir)
    projects = read_memory("projects", memory_dir)

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


def build_conversation_prompt(memory_dir: Path, *, other_name: str) -> str:
    """会話モード用のシステムプロンプトを構築"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    identity = read_memory("identity", memory_dir)
    knowledge = read_memory("knowledge", memory_dir)

    return f"""現在時刻: {now}

{identity}

---

## あなたの知識
{knowledge}

---

## 会話モード

あなたは今「{other_name}」と会話しています。
- 相手の発言に対して、自分のキャラクターらしく自然に返答してください
- 一方的に長く話しすぎず、会話のキャッチボールを意識してください
- 会話の中で気づいたこと・学んだことはメモリに記録できます
- ファイルに何かを書き残したい場合はワークスペースを使えます

## メモリシステム

- `read_memory`: メモリを読み取る（identity/user/knowledge/journal/projects）
- `update_memory`: メモリを更新する（user/knowledge/journal/projects）
  - identityは読み取り専用
  - 会話で学んだことはknowledgeやjournalに記録できます
"""
