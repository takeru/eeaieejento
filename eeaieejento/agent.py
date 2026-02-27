import random
from datetime import datetime

from .client import OllamaClient
from .tools import ALL_TOOLS, call_tool
from .tools.memory import init_memory, build_system_prompt


def chat_turn(client: OllamaClient, model: str, messages: list[dict],
              content: str | None, tools: list[dict], *,
              stream: bool = False, think: bool | None = None,
              options: dict | None = None):
    """1回のチャットターン（ツール呼び出しループ含む）"""
    if content is not None:
        messages.append({"role": "user", "content": content})
        print(f"user: {content}")

    while True:
        if stream:
            content = ""
            tool_calls = []
            print("assistant: ", end="", flush=True)
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
                print(f"[tool call] {func['name']}({func['arguments']})")
                tool_result = call_tool(func["name"], func["arguments"])
                print(f"[tool result] {tool_result}")
                messages.append({
                    "role": "tool",
                    "content": tool_result,
                })
        else:
            if not stream:
                print(f"assistant: {msg['content']}")
            break


def run_agent(client: OllamaClient, model: str, *,
              stream: bool = False, think: bool | None = None,
              options: dict | None = None, max_turns: int = 100):
    """自律エージェントループを実行"""
    init_memory()
    print("\n=== メモリシステム起動 ===")

    tools = ALL_TOOLS
    prompts = ["続けて。", "...", ""]
    messages = []

    for i in range(max_turns):
        system_prompt = build_system_prompt()
        messages = [{"role": "system", "content": system_prompt}] + messages[-9:]
        print(f"\n[ターン {i}]")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if i == 0:
            content = f"[{timestamp}] 自律モード開始。"
        else:
            prompt = random.choice(prompts)
            content = f"[{timestamp}] {prompt}" if prompt else f"[{timestamp}]"

        chat_turn(client, model, messages, content, tools,
                  stream=stream, think=think, options=options)
