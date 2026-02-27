import argparse

from .client import OllamaClient
from .agent import run_agent, list_personas, create_persona


def main():
    parser = argparse.ArgumentParser(description="自律AIエージェント")
    parser.add_argument("--model", "-m", help="使用するモデル名")
    parser.add_argument("--persona", "-p", default="default", help="ペルソナ名（デフォルト: default）")
    parser.add_argument("--list-personas", action="store_true", help="利用可能なペルソナ一覧を表示")
    parser.add_argument("--create-persona", metavar="NAME", help="新しいペルソナを作成")
    parser.add_argument("--think", action="store_true", help="thinkingモードを有効化")
    parser.add_argument("--no-think", action="store_true", help="thinkingモードを無効化")
    parser.add_argument("--stream", action="store_true", help="ストリーミング出力を有効化")
    parser.add_argument("--temperature", "-t", type=float, help="温度（0.0-2.0）")
    args = parser.parse_args()

    if args.list_personas:
        personas = list_personas()
        if personas:
            print("=== ペルソナ一覧 ===")
            for name in personas:
                print(f"  - {name}")
        else:
            print("ペルソナがありません。--create-persona NAME で作成してください")
        return

    if args.create_persona:
        name = args.create_persona
        persona_dir = create_persona(name)
        print(f"ペルソナ「{name}」を作成しました: {persona_dir}")
        print(f"identity を編集: {persona_dir / 'memory' / 'identity.md'}")
        return

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
              persona=args.persona,
              stream=args.stream, think=think, options=options)
