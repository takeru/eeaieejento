WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "指定した都市の天気を取得する",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "都市名（例: 東京、大阪、ニューヨーク）"
                }
            },
            "required": ["city"]
        }
    }
}


def get_weather(city: str) -> str:
    """天気を返すダミー関数"""
    weather_data = {
        "東京": "はれ",
        "大阪": "ぶた",
        "ニューヨーク": "ブリザード",
    }
    return weather_data.get(city, "不明")
