import json
import random
from datetime import datetime
from pathlib import Path

from .client import OllamaClient
from .tools import ALL_TOOLS, CONVERSATION_TOOLS, call_tool
from .tools.memory import MEMORY_TOOLS, init_memory, build_system_prompt, build_conversation_prompt

PERSONAS_DIR = Path.cwd() / "personas"
LOGS_DIR = Path.cwd() / "logs"


def resolve_persona(persona: str) -> tuple[Path, Path]:
    """ペルソナ名からメモリディレクトリとワークスペースディレクトリを解決"""
    persona_dir = PERSONAS_DIR / persona
    memory_dir = persona_dir / "memory"
    workspace_dir = persona_dir / "workspace"
    return memory_dir, workspace_dir


def list_personas() -> list[str]:
    """利用可能なペルソナ一覧を返す"""
    if not PERSONAS_DIR.exists():
        return []
    return sorted(
        d.name for d in PERSONAS_DIR.iterdir()
        if d.is_dir() and (d / "memory").exists()
    )


def create_persona(name: str) -> Path:
    """新しいペルソナを作成してディレクトリを返す"""
    memory_dir, workspace_dir = resolve_persona(name)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    init_memory(memory_dir)
    return PERSONAS_DIR / name


def chat_turn(client: OllamaClient, model: str, messages: list[dict],
              content: str | None, tools: list[dict], *,
              memory_dir: Path, workspace_dir: Path,
              stream: bool = False, think: bool | None = None,
              options: dict | None = None,
              label: str | None = None) -> tuple[str, list[dict]]:
    """1回のチャットターン（ツール呼び出しループ含む）。(最終発言, ツール呼び出しリスト)を返す"""
    prefix = f"{label}: " if label else "assistant: "
    tool_log: list[dict] = []

    if content is not None:
        messages.append({"role": "user", "content": content})

    while True:
        if stream:
            content = ""
            tool_calls = []
            print(prefix, end="", flush=True)
            for chunk in client.chat_stream(model, messages, think=think, tools=tools, options=options):
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
            result = client.chat(model, messages, tools=tools, think=think, options=options)
            msg = result["message"]

        messages.append(msg)

        if msg.get("tool_calls"):
            for tool_call in msg["tool_calls"]:
                func = tool_call["function"]
                name = func["name"]
                print(f"  [{name}({func['arguments']})]")
                if name == "end_conversation":
                    reason = func["arguments"].get("reason", "")
                    tool_result = f"会話終了を希望しました。{reason}"
                else:
                    tool_result = call_tool(name, func["arguments"],
                                            memory_dir=memory_dir, workspace_dir=workspace_dir)
                print(f"  → {tool_result}")
                tool_log.append({"name": name, "arguments": func["arguments"], "result": tool_result})
                messages.append({
                    "role": "tool",
                    "content": tool_result,
                })
        else:
            if not stream:
                print(f"{prefix}{msg['content']}")
            return msg.get("content", ""), tool_log


def run_agent(client: OllamaClient, model: str, *,
              persona: str = "default",
              stream: bool = False, think: bool | None = None,
              options: dict | None = None, max_turns: int = 100):
    """自律エージェントループを実行"""
    memory_dir, workspace_dir = resolve_persona(persona)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    init_memory(memory_dir)

    print(f"\n=== ペルソナ「{persona}」起動 ===")
    print(f"メモリ: {memory_dir}")
    print(f"ワークスペース: {workspace_dir}")

    tools = ALL_TOOLS
    prompts = ["続けて。", "...", ""]
    messages = []

    for i in range(max_turns):
        system_prompt = build_system_prompt(memory_dir)
        messages = [{"role": "system", "content": system_prompt}] + messages[-9:]
        print(f"\n[ターン {i}]")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if i == 0:
            content = f"[{timestamp}] 自律モード開始。"
        else:
            prompt = random.choice(prompts)
            content = f"[{timestamp}] {prompt}" if prompt else f"[{timestamp}]"

        chat_turn(client, model, messages, content, tools,
                  memory_dir=memory_dir, workspace_dir=workspace_dir,
                  stream=stream, think=think, options=options)


def run_conversation(client: OllamaClient, model: str, *,
                     persona_a: str, persona_b: str,
                     stream: bool = False, think: bool | None = None,
                     options: dict | None = None, max_turns: int = 20):
    """2人のペルソナで会話させる"""
    mem_a, ws_a = resolve_persona(persona_a)
    mem_b, ws_b = resolve_persona(persona_b)
    ws_a.mkdir(parents=True, exist_ok=True)
    ws_b.mkdir(parents=True, exist_ok=True)
    init_memory(mem_a)
    init_memory(mem_b)

    # ログファイル準備
    LOGS_DIR.mkdir(exist_ok=True)
    now = datetime.now()
    log_path = LOGS_DIR / f"{persona_a}_x_{persona_b}_{now.strftime('%Y%m%d_%H%M%S')}.jsonl"

    def write_log(log, event: str, **data):
        record = {"time": datetime.now().isoformat(), "event": event, **data}
        log.write(json.dumps(record, ensure_ascii=False) + "\n")
        log.flush()

    with open(log_path, "w") as log:
        write_log(log, "start", persona_a=persona_a, persona_b=persona_b, model=model)
        print(f"\n=== 会話: {persona_a} × {persona_b} ===")
        print(f"ログ: {log_path}\n")

        tools = CONVERSATION_TOOLS
        messages_a: list[dict] = []
        messages_b: list[dict] = []

        last_utterance = ""
        prev_ended = False

        for i in range(max_turns):
            is_a_turn = (i % 2 == 0)
            name = persona_a if is_a_turn else persona_b
            other = persona_b if is_a_turn else persona_a
            mem = mem_a if is_a_turn else mem_b
            ws = ws_a if is_a_turn else ws_b
            msgs = messages_a if is_a_turn else messages_b

            sys_prompt = build_conversation_prompt(mem, other_name=other)
            msgs_tail = [m for m in msgs if m["role"] != "system"][-9:]
            msgs.clear()
            msgs.append({"role": "system", "content": sys_prompt})
            msgs.extend(msgs_tail)

            if i == 0:
                user_content = f"（{other}との会話が始まった。まず自分から話しかけよう。）"
            else:
                user_content = last_utterance

            print(f"[{i}] ", end="")
            last_utterance, tool_calls = chat_turn(
                client, model, msgs, user_content, tools,
                memory_dir=mem, workspace_dir=ws,
                stream=stream, think=think, options=options,
                label=name,
            )

            write_log(log, "turn", turn=i, persona=name,
                      content=last_utterance, tool_calls=tool_calls)

            used_names = {tc["name"] for tc in tool_calls}
            if "end_conversation" in used_names:
                if prev_ended:
                    write_log(log, "end", reason="both_ended")
                    print(f"\n=== 2人とも会話終了を選択。会話を終了します ===")
                    break
                prev_ended = True
            else:
                prev_ended = False
        else:
            write_log(log, "end", reason="max_turns", max_turns=max_turns)
            print(f"\n=== {max_turns}ターン経過。会話を終了します ===")

        # 会話終了後、各ペルソナに振り返りとメモリ更新の機会を与える
        print(f"\n=== 振り返り ===\n")
        memory_tools = MEMORY_TOOLS
        for name, mem, ws, msgs in [
            (persona_a, mem_a, ws_a, messages_a),
            (persona_b, mem_b, ws_b, messages_b),
        ]:
            sys_prompt = build_conversation_prompt(mem, other_name="")
            msgs_tail = [m for m in msgs if m["role"] != "system"][-9:]
            msgs.clear()
            msgs.append({"role": "system", "content": sys_prompt})
            msgs.extend(msgs_tail)

            reflection, reflection_tools = chat_turn(
                client, model, msgs,
                "（会話が終わった。振り返って、覚えておきたいことや感じたことがあればメモリに記録しよう。）",
                memory_tools,
                memory_dir=mem, workspace_dir=ws,
                stream=stream, think=think, options=options,
                label=f"{name}(振り返り)",
            )
            write_log(log, "reflection", persona=name,
                      content=reflection, tool_calls=reflection_tools)

    print(f"\nログ保存: {log_path}")
