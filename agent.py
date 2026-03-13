import json
import os
import sys

import requests
from dotenv import load_dotenv


load_dotenv(".env.agent.secret")

API_KEY = os.getenv("LLM_API_KEY")
API_BASE = os.getenv("LLM_API_BASE")
MODEL = os.getenv("LLM_MODEL")


def call_llm(question: str) -> dict:
    if not API_KEY or not API_BASE or not MODEL:
        raise RuntimeError("Missing LLM_API_KEY, LLM_API_BASE, or LLM_MODEL in .env.agent.secret")

    url = f"{API_BASE.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Answer briefly and clearly.",
            },
            {
                "role": "user",
                "content": question,
            },
        ],
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()

    answer = data["choices"][0]["message"]["content"]

    return {
        "answer": answer,
        "tool_calls": [],
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    try:
        result = call_llm(question)
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()