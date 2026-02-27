import argparse
import random
from pathlib import Path

from .client import OllamaClient
from .agent import run_agent, run_conversation, load_conversation_log, list_personas, create_persona


def main():
    parser = argparse.ArgumentParser(description="自律AIエージェント")
    parser.add_argument("--model", "-m", help="使用するモデル名")
    parser.add_argument("--persona", "-p", default="default", help="ペルソナ名（デフォルト: default）")
    parser.add_argument("--talk", nargs="*", metavar="PERSONA", help="2人のペルソナで会話させる（省略でランダム）")
    parser.add_argument("--resume", metavar="LOG_FILE", help="ログファイルから会話を再開")
    parser.add_argument("--list-personas", action="store_true", help="利用可能なペルソナ一覧を表示")
    parser.add_argument("--create-persona", metavar="NAME", help="新しいペルソナを作成")
    parser.add_argument("--think", action="store_true", help="thinkingモードを有効化")
    parser.add_argument("--no-think", action="store_true", help="thinkingモードを無効化")
    parser.add_argument("--no-stream", action="store_true", help="ストリーミング出力を無効化")
    parser.add_argument("--max-turns", type=int, help="最大ターン数")
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

    print(f"\n=== {model_name} (think={think}, stream={not args.no_stream}) ===")

    if args.resume:
        log_file = Path(args.resume)
        if not log_file.exists():
            print(f"ログファイルが見つかりません: {log_file}")
            return
        state = load_conversation_log(log_file)
        kwargs = dict(persona_a=state["persona_a"], persona_b=state["persona_b"],
                      stream=not args.no_stream, think=think, options=options,
                      resume_from=log_file)
        if args.max_turns:
            kwargs["max_turns"] = args.max_turns
        run_conversation(client, model_name, **kwargs)
    elif args.talk is not None:
        talk = args.talk
        if len(talk) == 0:
            personas = list_personas()
            if len(personas) < 2:
                print("ペルソナが2つ以上必要です。--create-persona NAME で作成してください")
                return
            talk = random.sample(personas, 2)
            print(f"ランダム選択: {talk[0]} × {talk[1]}")
        elif len(talk) == 1:
            personas = [p for p in list_personas() if p != talk[0]]
            if not personas:
                print("他のペルソナがありません。--create-persona NAME で作成してください")
                return
            talk.append(random.choice(personas))
            print(f"ランダム選択: {talk[0]} × {talk[1]}")
        elif len(talk) > 2:
            print("--talk に指定できるペルソナは最大2つです")
            return
        kwargs = dict(persona_a=talk[0], persona_b=talk[1],
                      stream=not args.no_stream, think=think, options=options)
        if args.max_turns:
            kwargs["max_turns"] = args.max_turns
        run_conversation(client, model_name, **kwargs)
    else:
        kwargs = dict(persona=args.persona,
                      stream=not args.no_stream, think=think, options=options)
        if args.max_turns:
            kwargs["max_turns"] = args.max_turns
        run_agent(client, model_name, **kwargs)
