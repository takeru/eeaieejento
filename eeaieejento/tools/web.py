import json as _json

import httpx
from ddgs import DDGS
import trafilatura

WEB_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "DuckDuckGoでWeb検索する。検索結果のタイトル・URL・概要を返す",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "検索クエリ"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大件数（デフォルト5）"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "URLからWebページの本文テキストを取得する",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "取得するURL"
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "http_request",
            "description": "任意のHTTPリクエストを送信する。APIコールに使う。レスポンスのステータスコードとボディを返す",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                        "description": "HTTPメソッド"
                    },
                    "url": {
                        "type": "string",
                        "description": "リクエストURL"
                    },
                    "headers": {
                        "type": "object",
                        "description": "リクエストヘッダー（例: {\"Authorization\": \"Bearer xxx\"}）"
                    },
                    "body": {
                        "type": "object",
                        "description": "リクエストボディ（JSON）。POST/PUT/PATCHで使用"
                    }
                },
                "required": ["method", "url"]
            }
        }
    }
]


def web_search(query: str, max_results: int = 5) -> str:
    """DuckDuckGoで検索"""
    try:
        results = DDGS().text(query, max_results=max_results)
        if not results:
            return "検索結果なし"
        lines = []
        for r in results:
            lines.append(f"- {r['title']}\n  {r['href']}\n  {r['body']}")
        return "\n".join(lines)
    except Exception as e:
        return f"検索エラー: {e}"


def web_fetch(url: str) -> str:
    """URLからWebページの本文を取得"""
    try:
        html = trafilatura.fetch_url(url)
        if html is None:
            return "ページを取得できませんでした"
        text = trafilatura.extract(html)
        if text is None:
            return "本文を抽出できませんでした"
        # 長すぎる場合は切り詰め
        if len(text) > 4000:
            text = text[:4000] + "\n...(以下省略)"
        return text
    except Exception as e:
        return f"取得エラー: {e}"


def http_request(method: str, url: str, headers: dict | None = None, body: dict | None = None) -> str:
    """任意のHTTPリクエストを送信"""
    try:
        with httpx.Client(timeout=30.0) as client:
            kwargs = {}
            if headers:
                kwargs["headers"] = headers
            if body and method in ("POST", "PUT", "PATCH"):
                kwargs["headers"] = {**(headers or {}), "Content-Type": "application/json"}
                if isinstance(body, str):
                    kwargs["content"] = body
                else:
                    kwargs["content"] = _json.dumps(body, ensure_ascii=False)

            response = client.request(method, url, **kwargs)

            result = f"HTTP {response.status_code}"
            content_type = response.headers.get("content-type", "")
            text = response.text
            if len(text) > 4000:
                text = text[:4000] + "\n...(以下省略)"
            result += f"\n{text}"
            return result
    except Exception as e:
        return f"リクエストエラー: {e}"
