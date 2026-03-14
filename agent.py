import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(".env.agent.secret")

API_KEY = os.getenv("LLM_API_KEY")
API_BASE = os.getenv("LLM_API_BASE")
MODEL = os.getenv("LLM_MODEL")

PROJECT_ROOT = Path(".").resolve()


# ------------------------
# TOOLS
# ------------------------

def read_file(path: str):
    try:
        if ".." in path:
            return "Error: path traversal not allowed"

        full_path = (PROJECT_ROOT / path).resolve()

        if not str(full_path).startswith(str(PROJECT_ROOT)):
            return "Error: access outside project not allowed"

        if not full_path.exists():
            return "Error: file not found"

        return full_path.read_text()

    except Exception as e:
        return f"Error: {str(e)}"


def list_files(path: str):
    try:
        if ".." in path:
            return "Error: path traversal not allowed"

        full_path = (PROJECT_ROOT / path).resolve()

        if not str(full_path).startswith(str(PROJECT_ROOT)):
            return "Error: access outside project not allowed"

        if not full_path.exists():
            return "Error: path not found"

        entries = os.listdir(full_path)
        return "\n".join(entries)

    except Exception as e:
        return f"Error: {str(e)}"


# ------------------------
# TOOL SCHEMAS
# ------------------------

tools = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to file"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path"
                    }
                },
                "required": ["path"]
            }
        }
    }
]


# ------------------------
# LLM CALL
# ------------------------

def call_llm(messages):
    if not API_KEY or not API_BASE or not MODEL:
        raise RuntimeError("Missing LLM_API_KEY, LLM_API_BASE, or LLM_MODEL")

    url = f"{API_BASE.rstrip('/')}/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": tools,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()

    return response.json()


# ------------------------
# AGENTIC LOOP
# ------------------------

def run_agent(question: str):

    messages = [
        {
            "role": "system",
            "content": (
                "You are a documentation agent. "
                "Use list_files to discover wiki files, then read_file to read them. "
                "Return the answer and include the source file path and section anchor."
            ),
        },
        {
            "role": "user",
            "content": question,
        },
    ]

    tool_history = []

    for _ in range(10):

        data = call_llm(messages)
        message = data["choices"][0]["message"]

        tool_calls = message.get("tool_calls")

        # ------------------------
        # If LLM wants to call tools
        # ------------------------

        if tool_calls:

            messages.append(message)

            for call in tool_calls:

                tool_name = call["function"]["name"]
                args = json.loads(call["function"]["arguments"])

                if tool_name == "read_file":
                    result = read_file(**args)

                elif tool_name == "list_files":
                    result = list_files(**args)

                else:
                    result = "Error: unknown tool"

                tool_history.append({
                    "tool": tool_name,
                    "args": args,
                    "result": result
                })

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": result,
                    }
                )

            continue

        # ------------------------
        # Final answer
        # ------------------------

        answer = message.get("content", "").strip()

        return {
            "answer": answer,
            "source": "unknown",
            "tool_calls": tool_history,
        }

    # fallback if 10 calls reached

    return {
        "answer": "Stopped after 10 tool calls",
        "source": "unknown",
        "tool_calls": tool_history,
    }


# ------------------------
# CLI
# ------------------------

def main():
    if len(sys.argv) < 2:
        print('Usage: uv run agent.py "question"', file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    try:
        result = run_agent(question)
        print(json.dumps(result, ensure_ascii=False))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
