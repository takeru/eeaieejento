from pathlib import Path

from .weather import WEATHER_TOOL, get_weather
from .file_ops import FILE_TOOLS, read_file, write_file, append_file, edit_file, delete_file, list_files, mkdir, grep_file, file_info
from .memory import MEMORY_TOOLS, read_memory, update_memory, init_memory, build_system_prompt

ALL_TOOLS = FILE_TOOLS + MEMORY_TOOLS


def call_tool(name: str, args: dict, *, memory_dir: Path, workspace_dir: Path) -> str:
    """ツール呼び出しのディスパッチ"""
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
    }
    handler = dispatch.get(name)
    if handler:
        return handler()
    return f"不明なツール: {name}"
