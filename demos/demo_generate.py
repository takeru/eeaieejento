"""generate API のデモ（単発プロンプトによるテキスト生成）"""

import argparse

from eeaieejento.client import OllamaClient


def main():
    parser = argparse.ArgumentParser(description="generate APIデモ")
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
    prompt = "こんにちは、自己紹介してください。"

    print(f"\n=== generate API ({model}, think={think}, stream={args.stream}) ===")

    if args.stream:
        print("response: ", end="", flush=True)
        for chunk in client.generate_stream(model, prompt, think=think):
            print(chunk.get("response", ""), end="", flush=True)
        print()
    else:
        response = client.generate(model, prompt, think=think)
        print(f"response: {response}")


if __name__ == "__main__":
    main()
