import argparse

from .client import OllamaClient
from .agent import run_agent


def main():
    parser = argparse.ArgumentParser(description="自律AIエージェント")
    parser.add_argument("--model", "-m", help="使用するモデル名")
    parser.add_argument("--think", action="store_true", help="thinkingモードを有効化")
    parser.add_argument("--no-think", action="store_true", help="thinkingモードを無効化")
    parser.add_argument("--stream", action="store_true", help="ストリーミング出力を有効化")
    parser.add_argument("--temperature", "-t", type=float, help="温度（0.0-2.0）")
    args = parser.parse_args()

    client = OllamaClient()

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

    think = None
    if args.think:
        think = True
    elif args.no_think:
        think = False

    options = {}
    if args.temperature is not None:
        options["temperature"] = args.temperature
    options = options or None

    print(f"\n=== {model_name} (think={think}, stream={args.stream}) ===")

    run_agent(client, model_name,
              stream=args.stream, think=think, options=options)
