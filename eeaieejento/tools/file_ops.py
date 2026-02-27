from datetime import datetime
from pathlib import Path

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


def safe_path(path: str, base_dir: Path) -> Path | None:
    """パスを検証し、base_dir内であれば絶対パスを返す。外部なら None"""
    try:
        resolved = (base_dir / path).resolve()
        if base_dir in resolved.parents or resolved == base_dir:
            return resolved
        return None
    except Exception:
        return None


def read_file(path: str, base_dir: Path, offset: int | None = None, limit: int | None = None) -> str:
    resolved = safe_path(path, base_dir)
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
        if offset is not None or limit is not None:
            start = offset or 0
            end = start + limit if limit else total
            lines = lines[start:end]
            header = f"[{path}: 行 {start+1}-{min(end, total)} / 全{total}行]\n"
            return header + "".join(lines)
        return content
    except Exception as e:
        return f"エラー: {e}"


def write_file(path: str, content: str, base_dir: Path) -> str:
    resolved = safe_path(path, base_dir)
    if resolved is None:
        return "エラー: ディレクトリ外へのアクセスは禁止されています"
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content)
        return f"書き込み完了: {path}"
    except Exception as e:
        return f"エラー: {e}"


def append_file(path: str, content: str, base_dir: Path) -> str:
    resolved = safe_path(path, base_dir)
    if resolved is None:
        return "エラー: ディレクトリ外へのアクセスは禁止されています"
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        with resolved.open("a") as f:
            f.write(content)
        return f"追記完了: {path}"
    except Exception as e:
        return f"エラー: {e}"


def delete_file(path: str, base_dir: Path) -> str:
    resolved = safe_path(path, base_dir)
    if resolved is None:
        return "エラー: ディレクトリ外へのアクセスは禁止されています"
    if not resolved.exists():
        return f"エラー: ファイルが存在しません: {path}"
    try:
        if resolved.is_file():
            resolved.unlink()
            return f"削除完了: {path}"
        elif resolved.is_dir():
            resolved.rmdir()
            return f"ディレクトリ削除完了: {path}"
        return f"エラー: 削除できません: {path}"
    except OSError as e:
        return f"エラー: {e}"


def mkdir(path: str, base_dir: Path) -> str:
    resolved = safe_path(path, base_dir)
    if resolved is None:
        return "エラー: ディレクトリ外へのアクセスは禁止されています"
    try:
        resolved.mkdir(parents=True, exist_ok=True)
        return f"ディレクトリ作成完了: {path}"
    except Exception as e:
        return f"エラー: {e}"


def grep_file(path: str, pattern: str, base_dir: Path) -> str:
    resolved = safe_path(path, base_dir)
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


def file_info(path: str, base_dir: Path) -> str:
    resolved = safe_path(path, base_dir)
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


def list_files(path: str, base_dir: Path) -> str:
    resolved = safe_path(path, base_dir)
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


def edit_file(path: str, search: str, replace: str, base_dir: Path) -> str:
    """ファイルの一部を編集する（Search/Replace形式）"""
    resolved = safe_path(path, base_dir)
    if resolved is None:
        return "エラー: ディレクトリ外へのアクセスは禁止されています"
    if not resolved.exists():
        return f"エラー: ファイルが存在しません: {path}"
    if not resolved.is_file():
        return f"エラー: ファイルではありません: {path}"
    try:
        content = resolved.read_text()
        if search not in content:
            normalized_content = " ".join(content.split())
            normalized_search = " ".join(search.split())
            if normalized_search not in normalized_content:
                return "エラー: 検索文字列が見つかりません"
            return "エラー: 検索文字列が見つかりません（空白やインデントが異なる可能性があります）"
        count = content.count(search)
        if count > 1:
            return f"エラー: 検索文字列が{count}箇所見つかりました。より具体的な文字列を指定してください"
        new_content = content.replace(search, replace, 1)
        resolved.write_text(new_content)
        return f"編集完了: {path}"
    except Exception as e:
        return f"エラー: {e}"
