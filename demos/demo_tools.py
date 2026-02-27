"""tool use のデモ（天気ツール + ファイル操作）"""

import argparse

from eeaieejento.client import OllamaClient
from eeaieejento.tools import call_tool
from eeaieejento.tools.weather import WEATHER_TOOL
from eeaieejento.tools.file_ops import FILE_TOOLS
from eeaieejento.agent import chat_turn


def main():
    parser = argparse.ArgumentParser(description="tool useデモ")
    parser.add_argument("--model", "-m", help="使用するモデル名")
    parser.add_argument("--think", action="store_true", help="thinkingモードを有効化")
    parser.add_argument("--no-think", action="store_true", help="thinkingモードを無効化")
    parser.add_argument("--stream", action="store_true", help="ストリーミング出力")
    parser.add_argument("--temperature", "-t", type=float, help="温度（0.0-2.0）")
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
    options = {}
    if args.temperature is not None:
        options["temperature"] = args.temperature
    options = options or None

    tools = [WEATHER_TOOL] + FILE_TOOLS

    print(f"\n=== tool useデモ ({model}) ===")

    messages = []
    chat_turn(client, model, messages, "ファイル一覧見せて", tools,
              stream=args.stream, think=think, options=options)
    chat_turn(client, model, messages, "東京の天気をtokyo.txtに書いて", tools,
              stream=args.stream, think=think, options=options)

    messages = []
    chat_turn(client, model, messages, "tokyo.txtの内容を教えて", tools,
              stream=args.stream, think=think, options=options)


if __name__ == "__main__":
    main()
