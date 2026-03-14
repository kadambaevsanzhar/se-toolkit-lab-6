import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# load env
load_dotenv(".env.agent.secret")
load_dotenv(".env.docker.secret")

API_KEY = os.getenv("LLM_API_KEY")
API_BASE = os.getenv("LLM_API_BASE")
MODEL = os.getenv("LLM_MODEL")

PROJECT_ROOT = Path(".").resolve()

# ------------------------
# TOOLS IMPLEMENTATION
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

        return "\n".join(os.listdir(full_path))

    except Exception as e:
        return f"Error: {str(e)}"


def query_api(method: str, path: str, body: str = None):
    try:
        base_url = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
        api_key = os.getenv("LMS_API_KEY")

        url = base_url.rstrip("/") + path

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=body
        )

        try:
            parsed = response.json()
        except Exception:
            parsed = response.text

        return json.dumps({
            "status_code": response.status_code,
            "body": parsed
        })

    except Exception as e:
        return json.dumps({
            "status_code": 500,
            "body": str(e)
        })


# ------------------------
# TOOL SCHEMAS
# ------------------------

tools = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the project repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory in the project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Call the running backend API to retrieve live system data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {"type": "string"},
                    "path": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["method", "path"]
            }
        }
    }
]

# ------------------------
# TOOL EXECUTION
# ------------------------

def execute_tool(name, args):
    if name == "read_file":
        return read_file(**args)
    if name == "list_files":
        return list_files(**args)
    if name == "query_api":
        return query_api(**args)

    return f"Unknown tool {name}"


# ------------------------
# AGENT LOOP
# ------------------------

def run_agent(question: str):

    messages = [
        {
            "role": "system",
            "content": (
                "You are a system agent. "
                "Use read_file for documentation and source code. "
                "Use list_files to explore the repository structure. "
                "Use query_api for live backend data such as item counts or endpoint responses."
            )
        },
        {"role": "user", "content": question}
    ]

    tool_calls_log = []

    for _ in range(6):

        resp = requests.post(
            f"{API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto"
            }
        )

        data = resp.json()
        msg = data["choices"][0]["message"]

        if msg.get("tool_calls"):
            messages.append(msg)

            for call in msg["tool_calls"]:
                name = call["function"]["name"]
                args = json.loads(call["function"]["arguments"])

                result = execute_tool(name, args)

                tool_calls_log.append({
                    "tool": name,
                    "args": args,
                    "result": result
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": result
                })

        else:
            answer = msg.get("content") or ""
            return {
                "answer": answer,
                "tool_calls": tool_calls_log
            }

    return {"answer": "Agent reached max iterations", "tool_calls": tool_calls_log}


# ------------------------
# CLI
# ------------------------

if __name__ == "__main__":
    question = " ".join(sys.argv[1:])
    result = run_agent(question)
    print(json.dumps(result, indent=2))
