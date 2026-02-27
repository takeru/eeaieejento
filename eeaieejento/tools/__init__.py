from pathlib import Path

from .weather import WEATHER_TOOL, get_weather
from .file_ops import FILE_TOOLS, read_file, write_file, append_file, edit_file, delete_file, list_files, mkdir, grep_file, file_info
from .memory import MEMORY_TOOLS, read_memory, update_memory, init_memory, build_system_prompt
from .web import WEB_TOOLS, web_search, web_fetch, http_request

END_CONVERSATION_TOOL = {
    "type": "function",
    "function": {
        "name": "end_conversation",
        "description": "会話を終了したいときに使う。2人が連続してこのツールを使うと会話が終了する",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "会話を終えたい理由（任意）"
                }
            }
        }
    }
}

ALL_TOOLS = FILE_TOOLS + MEMORY_TOOLS + WEB_TOOLS
CONVERSATION_TOOLS = ALL_TOOLS + [END_CONVERSATION_TOOL]

# ツール名 → required パラメータのマッピングを構築
_TOOL_SCHEMA: dict[str, list[str]] = {}
for _tool in CONVERSATION_TOOLS:
    _func = _tool["function"]
    _TOOL_SCHEMA[_func["name"]] = _func["parameters"].get("required", [])


def _validate_args(name: str, args: dict) -> str | None:
    """必須パラメータの検証。エラーがあればメッセージを返す"""
    required = _TOOL_SCHEMA.get(name, [])
    missing = [r for r in required if r not in args]
    if missing:
        return f"エラー: {name}() に必須パラメータが不足: {', '.join(missing)}。必要: {', '.join(required)}"
    return None


def call_tool(name: str, args: dict, *, memory_dir: Path, workspace_dir: Path) -> str:
    """ツール呼び出しのディスパッチ"""
    # 必須パラメータの検証
    error = _validate_args(name, args)
    if error:
        return error

    dispatch = {
        "get_weather": lambda: get_weather(args["city"]),
        "read_file": lambda: read_file(args["path"], workspace_dir, args.get("offset"), args.get("limit")),
        "write_file": lambda: write_file(args["path"], args["content"], workspace_dir),
        "append_file": lambda: append_file(args["path"], args["content"], workspace_dir),
        "edit_file": lambda: edit_file(args["path"], args["search"], args["replace"], workspace_dir),
        "delete_file": lambda: delete_file(args["path"], workspace_dir),
        "list_files": lambda: list_files(args["path"], workspace_dir),
        "mkdir": lambda: mkdir(args["path"], workspace_dir),
        "grep_file": lambda: grep_file(args["path"], args["pattern"], workspace_dir),
        "file_info": lambda: file_info(args["path"], workspace_dir),
        "read_memory": lambda: read_memory(args["category"], memory_dir),
        "update_memory": lambda: update_memory(args["category"], args["content"], args["mode"], memory_dir),
        "web_search": lambda: web_search(args["query"], args.get("max_results", 5)),
        "web_fetch": lambda: web_fetch(args["url"]),
        "http_request": lambda: http_request(args["method"], args["url"], args.get("headers"), args.get("body")),
    }
    handler = dispatch.get(name)
    if handler:
        return handler()
    return f"不明なツール: {name}"
