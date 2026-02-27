"""chat API のデモ（マルチターン会話）"""

import argparse

from eeaieejento.client import OllamaClient


def main():
    parser = argparse.ArgumentParser(description="chat APIデモ")
    parser.add_argument("--model", "-m", help="使用するモデル名")
    parser.add_argument("--think", action="store_true", help="thinkingモードを有効化")
    parser.add_argument("--no-think", action="store_true", help="thinkingモードを無効化")
    parser.add_argument("--stream", action="store_true", help="ストリーミング出力")
    args = parser.parse_args()

    client = OllamaClient()

    models = client.list_models()
    print("=== 利用可能なモデル ===")
    for m in models:
        print(f"  - {m['name']}")

    model = args.model or (models[0]["name"] if models else None)
    if not model:
        print("モデルがありません。ollama pull <model> でダウンロードしてください")
        return

    think = True if args.think else (False if args.no_think else None)

    print(f"\n=== chat API ({model}, think={think}, stream={args.stream}) ===")

    messages = []

    if args.stream:
        def chat(content):
            messages.append({"role": "user", "content": content})
            print(f"user: {content}")
            print("assistant: ", end="", flush=True)
            response_content = ""
            for chunk in client.chat_stream(model, messages, think=think):
                msg = chunk.get("message", {})
                if msg.get("content"):
                    print(msg["content"], end="", flush=True)
                    response_content += msg["content"]
            messages.append({"role": "assistant", "content": response_content})
            print()
    else:
        def chat(content):
            messages.append({"role": "user", "content": content})
            print(f"user: {content}")
            result = client.chat(model, messages=messages, think=think)
            if "thinking" in result.get("message", {}):
                print(f"thinking: {result['message']['thinking']}")
            print(f"assistant: {result['message']['content']}")

    chat("1+1は？")
    chat("さらに+4は？")


if __name__ == "__main__":
    main()
