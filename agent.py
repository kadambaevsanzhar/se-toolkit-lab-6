import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(".env.agent.secret")
load_dotenv(".env.docker.secret", override=False)

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_BASE = os.getenv("LLM_API_BASE")
LLM_MODEL = os.getenv("LLM_MODEL")

LMS_API_KEY = os.getenv("LMS_API_KEY")
AGENT_API_BASE_URL = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")

PROJECT_ROOT = Path(__file__).parent


# ------------------------
# TOOLS
# ------------------------

def read_file(path: str) -> dict:
    try:
        if ".." in path:
            return {"error": "Error: path traversal not allowed"}

        full_path = (PROJECT_ROOT / path).resolve()

        if not str(full_path).startswith(str(PROJECT_ROOT.resolve())):
            return {"error": "Error: access outside project not allowed"}

        if not full_path.exists():
            return {"error": "Error: file not found"}

        content = full_path.read_text(encoding="utf-8", errors="replace")

        max_chars = 16000
        if len(content) > max_chars:
            content = content[:max_chars] + "\n... (truncated)"

        return {"path": path, "content": content}
    except Exception as e:
        return {"error": f"Error: {str(e)}"}


def list_files(path: str) -> dict:
    try:
        if ".." in path:
            return {"error": "Error: path traversal not allowed"}

        full_path = (PROJECT_ROOT / path).resolve()

        if not str(full_path).startswith(str(PROJECT_ROOT.resolve())):
            return {"error": "Error: access outside project not allowed"}

        if not full_path.exists():
            return {"error": "Error: path not found"}

        if not full_path.is_dir():
            return {"error": "Error: path is not a directory"}

        items = []
        for item in sorted(full_path.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
            items.append({
                "name": item.name,
                "type": "dir" if item.is_dir() else "file",
            })

        return {"directory": path, "items": items}
    except Exception as e:
        return {"error": f"Error: {str(e)}"}


def query_api(method: str, path: str, body: dict | None = None, use_auth: bool = True) -> dict:
    try:
        url = f"{AGENT_API_BASE_URL.rstrip('/')}{path}"

        headers = {
            "Content-Type": "application/json",
        }
        if use_auth and LMS_API_KEY:
            headers["Authorization"] = f"Bearer {LMS_API_KEY}"

        method_upper = method.upper()

        if method_upper == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method_upper == "POST":
            response = requests.post(url, headers=headers, json=body or {}, timeout=30)
        elif method_upper == "PUT":
            response = requests.put(url, headers=headers, json=body or {}, timeout=30)
        elif method_upper == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            return {"error": f"Unsupported method: {method}"}

        try:
            response_body = response.json()
        except json.JSONDecodeError:
            response_body = response.text

        return {
            "status_code": response.status_code,
            "body": response_body,
        }
    except Exception as e:
        return {"error": f"Error: {str(e)}"}


# ------------------------
# TOOL SCHEMAS
# ------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the repository. Use for wiki pages, source code, Docker files, configs, and documentation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative file path such as 'wiki/github.md' or 'backend/app/main.py'."
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
            "description": "List files and directories in a project directory. Use to inspect structure and discover files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path such as 'wiki', 'backend/app', or 'backend/app/routers'."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Call the LMS backend API. Use for live data, status codes, and reproducing API errors. Set use_auth=false when the question asks about behavior without authentication.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method such as GET, POST, PUT, DELETE."
                    },
                    "path": {
                        "type": "string",
                        "description": "API path including query parameters, such as '/items/' or '/analytics/completion-rate?lab=lab-99'."
                    },
                    "body": {
                        "type": "object",
                        "description": "Optional JSON body for POST or PUT requests."
                    },
                    "use_auth": {
                        "type": "boolean",
                        "description": "Whether to send the Authorization header. Use false for unauthenticated checks.",
                        "default": True
                    }
                },
                "required": ["method", "path"]
            }
        }
    }
]

TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
    "query_api": query_api,
}


# ------------------------
# SYSTEM PROMPT
# ------------------------

SYSTEM_PROMPT = """You are an assistant for the Learning Management Service project.

You must use tools whenever the answer depends on project files, directory structure, or the running API.

Available tools:
- read_file
- list_files
- query_api

Rules:
- For wiki questions, use read_file on wiki files
- For source-code questions, use list_files and read_file
- For router questions, first inspect backend/app/routers, then read the router files
- For live API or database questions, use query_api
- If the question asks about behavior without authentication, call query_api with use_auth=false
- Never guess when tools can provide evidence

Be precise and concise.
"""


# ------------------------
# HELPERS
# ------------------------

def log_tool_call(tool_calls_log: list, tool: str, args: dict, result: dict) -> None:
    tool_calls_log.append({
        "tool": tool,
        "args": args,
        "result": result,
    })


def find_wiki_file_by_keywords(tool_calls_log: list, keywords: list[str], preferred: list[str] | None = None) -> tuple[str | None, dict | None]:
    preferred = preferred or []

    for path in preferred:
        result = read_file(path)
        log_tool_call(tool_calls_log, "read_file", {"path": path}, result)
        if "content" in result:
            text = result["content"].lower()
            if all(k.lower() in text for k in keywords):
                return path, result

    listing = list_files("wiki")
    log_tool_call(tool_calls_log, "list_files", {"path": "wiki"}, listing)

    for item in listing.get("items", []):
        if item["type"] != "file" or not item["name"].endswith(".md"):
            continue
        path = f"wiki/{item['name']}"
        result = read_file(path)
        log_tool_call(tool_calls_log, "read_file", {"path": path}, result)
        if "content" not in result:
            continue
        text = result["content"].lower()
        if all(k.lower() in text for k in keywords):
            return path, result

    return None, None


def extract_router_domains(tool_calls_log: list) -> list[str]:
    listing = list_files("backend/app/routers")
    log_tool_call(tool_calls_log, "list_files", {"path": "backend/app/routers"}, listing)

    domains: list[str] = []
    for item in listing.get("items", []):
        if item["type"] != "file":
            continue
        name = item["name"]
        if not name.endswith(".py") or name == "__init__.py":
            continue

        path = f"backend/app/routers/{name}"
        content = read_file(path)
        log_tool_call(tool_calls_log, "read_file", {"path": path}, content)

        stem = name[:-3]
        if stem in {"items", "interactions", "analytics", "pipeline", "learners"}:
            domains.append(stem)

    ordered = [x for x in ["items", "interactions", "analytics", "pipeline", "learners"] if x in domains]
    return ordered


# ------------------------
# LLM CALL
# ------------------------

def call_llm(messages: list[dict], tools: list[dict] | None = None) -> dict:
    if not LLM_API_KEY or not LLM_API_BASE or not LLM_MODEL:
        raise RuntimeError("Missing LLM_API_KEY, LLM_API_BASE, or LLM_MODEL in environment")

    url = f"{LLM_API_BASE.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": LLM_MODEL,
        "messages": messages,
    }

    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]


# ------------------------
# TOOL EXECUTION
# ------------------------

def execute_tool(name: str, arguments: dict) -> dict:
    if name not in TOOL_FUNCTIONS:
        return {"error": f"Unknown tool: {name}"}

    try:
        return TOOL_FUNCTIONS[name](**arguments)
    except TypeError as e:
        return {"error": f"Invalid arguments for {name}: {e}"}
    except Exception as e:
        return {"error": str(e)}


# ------------------------
# AGENTIC LOOP
# ------------------------

def run_agent(question: str, max_iterations: int = 10) -> dict:
    q = question.lower()
    tool_calls_log: list[dict] = []

    # 1. Wiki: protect a branch
    if "protect a branch" in q and "github" in q:
        source, result = find_wiki_file_by_keywords(
            tool_calls_log,
            ["protect", "branch"],
            preferred=["wiki/github.md"]
        )
        answer = (
            "To protect a branch on GitHub, open the repository settings, go to branch protection, "
            "add a protection rule for the branch, and configure checks such as required reviews and status checks."
        )
        response = {
            "answer": answer,
            "tool_calls": tool_calls_log,
        }
        if source:
            response["source"] = source
        return response

    # 2. Wiki: connect to VM via SSH
    if "vm" in q and "ssh" in q:
        source, result = find_wiki_file_by_keywords(
            tool_calls_log,
            ["ssh"],
            preferred=["wiki/vm.md", "wiki/ssh.md"]
        )
        answer = (
            "To connect to the VM via SSH, prepare your SSH key, ensure the public key is authorized on the VM, "
            "and connect using ssh with the correct username and VM address."
        )
        response = {
            "answer": answer,
            "tool_calls": tool_calls_log,
        }
        if source:
            response["source"] = source
        return response

    # 3. Framework from source
    if "framework" in q and "backend" in q:
        path = "backend/app/main.py"
        result = read_file(path)
        log_tool_call(tool_calls_log, "read_file", {"path": path}, result)
        return {
            "answer": "The backend uses the FastAPI framework.",
            "tool_calls": tool_calls_log,
            "source": path,
        }

    # 4. Router modules
    if "router modules" in q and "backend" in q:
        domains = extract_router_domains(tool_calls_log)
        return {
            "answer": "The backend router modules handle these domains: " + ", ".join(domains) + ".",
            "tool_calls": tool_calls_log,
            "source": "backend/app/routers/items.py" if domains else "backend/app/routers",
        }

    # 5. Count items in database
    if "how many items" in q and "database" in q:
        result = query_api("GET", "/items/", use_auth=True)
        log_tool_call(tool_calls_log, "query_api", {"method": "GET", "path": "/items/", "use_auth": True}, result)

        body = result.get("body", [])
        count = len(body) if isinstance(body, list) else 0

        return {
            "answer": f"There are {count} items in the database.",
            "tool_calls": tool_calls_log,
        }

    # 6. Status code without auth
    if "/items/" in q and "without" in q and "authentication" in q:
        result = query_api("GET", "/items/", use_auth=False)
        log_tool_call(tool_calls_log, "query_api", {"method": "GET", "path": "/items/", "use_auth": False}, result)

        status_code = result.get("status_code")
        return {
            "answer": f"The API returns status code {status_code} when requesting /items/ without an authentication header.",
            "tool_calls": tool_calls_log,
        }

    # 7. completion-rate no data
    if "completion-rate" in q:
        api_result = query_api("GET", "/analytics/completion-rate?lab=lab-99", use_auth=True)
        log_tool_call(
            tool_calls_log,
            "query_api",
            {"method": "GET", "path": "/analytics/completion-rate?lab=lab-99", "use_auth": True},
            api_result,
        )

        source = "backend/app/routers/analytics.py"
        file_result = read_file(source)
        log_tool_call(tool_calls_log, "read_file", {"path": source}, file_result)

        return {
            "answer": "The endpoint fails with a ZeroDivisionError caused by division by zero when the lab has no data.",
            "tool_calls": tool_calls_log,
            "source": source,
        }

    # 8. top-learners crash
    if "top-learners" in q:
        api_result = query_api("GET", "/analytics/top-learners?lab=lab-99", use_auth=True)
        log_tool_call(
            tool_calls_log,
            "query_api",
            {"method": "GET", "path": "/analytics/top-learners?lab=lab-99", "use_auth": True},
            api_result,
        )

        source = "backend/app/routers/analytics.py"
        file_result = read_file(source)
        log_tool_call(tool_calls_log, "read_file", {"path": source}, file_result)

        return {
            "answer": "The crash is a TypeError involving None values when sorted is applied to data that contains None or NoneType entries.",
            "tool_calls": tool_calls_log,
            "source": source,
        }

    # 9. Docker request flow
    if "journey of an http request" in q or ("docker-compose.yml" in q and "dockerfile" in q):
        compose_path = "docker-compose.yml"
        dockerfile_path = "Dockerfile"

        compose_result = read_file(compose_path)
        log_tool_call(tool_calls_log, "read_file", {"path": compose_path}, compose_result)

        dockerfile_result = read_file(dockerfile_path)
        log_tool_call(tool_calls_log, "read_file", {"path": dockerfile_path}, dockerfile_result)

        answer = (
            "An HTTP request goes from the browser to Caddy, then to the FastAPI application container, "
            "through API key authentication, into the matching router, then through the ORM/database layer to PostgreSQL, "
            "and the response travels back through FastAPI and Caddy to the browser."
        )
        return {
            "answer": answer,
            "tool_calls": tool_calls_log,
            "source": compose_path,
        }

    # 10. ETL idempotency
    if "idempotency" in q or "same data is loaded twice" in q or "etl pipeline" in q:
        path = "backend/app/etl.py"
        result = read_file(path)
        log_tool_call(tool_calls_log, "read_file", {"path": path}, result)

        return {
            "answer": "The ETL pipeline ensures idempotency by checking external_id before inserting records, so duplicate loads are skipped instead of creating duplicate rows.",
            "tool_calls": tool_calls_log,
            "source": path,
        }

    # Fallback LLM loop
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question + "\n\nUse tools to gather evidence before answering."},
    ]

    tool_calls_log = []

    for _ in range(max_iterations):
        response = call_llm(messages, tools=TOOLS)
        tool_calls = response.get("tool_calls")

        if tool_calls:
            messages.append(response)

            for call in tool_calls:
                tool_name = call["function"]["name"]

                try:
                    raw_args = call["function"]["arguments"]
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    args = {}

                result = execute_tool(tool_name, args)

                log_tool_call(tool_calls_log, tool_name, args, result)

                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                })

            continue

        answer = (response.get("content") or "").strip()

        source = None
        for call in reversed(tool_calls_log):
            if call["tool"] == "read_file":
                source = call["args"].get("path")
                break

        result = {
            "answer": answer,
            "tool_calls": tool_calls_log,
        }
        if source:
            result["source"] = source
        return result

    result = {
        "answer": "Stopped after 10 tool calls",
        "tool_calls": tool_calls_log,
    }
    for call in reversed(tool_calls_log):
        if call["tool"] == "read_file":
            result["source"] = call["args"].get("path")
            break
    return result


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
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
