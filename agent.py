import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv(".env.agent.secret")
load_dotenv(".env.docker.secret", override=False)

# LLM configuration
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_BASE = os.getenv("LLM_API_BASE")
LLM_MODEL = os.getenv("LLM_MODEL")

# Backend API configuration
LMS_API_KEY = os.getenv("LMS_API_KEY")
AGENT_API_BASE_URL = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")

# Project root for file operations
PROJECT_ROOT = Path(__file__).parent


def call_llm(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """Call the LLM API with optional function calling support."""
    if not LLM_API_KEY or not LLM_API_BASE or not LLM_MODEL:
        raise RuntimeError("Missing LLM_API_KEY, LLM_API_BASE, or LLM_MODEL in .env.agent.secret")

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


def read_file(path: str) -> dict:
    """Read a file from the project."""
    try:
        full_path = (PROJECT_ROOT / path).resolve()
        # Security: ensure path is within project root
        if not str(full_path).startswith(str(PROJECT_ROOT.resolve())):
            return {"error": f"Access denied: path outside project root"}
        if not full_path.exists():
            return {"error": f"File not found: {path}"}
        content = full_path.read_text(encoding="utf-8")
        # Truncate if too large
        max_chars = 8000
        if len(content) > max_chars:
            content = content[:max_chars] + "\n... (truncated)"
        return {"path": path, "content": content}
    except Exception as e:
        return {"error": str(e)}


def list_files(dir_path: str = ".") -> dict:
    """List files in a directory."""
    try:
        full_path = (PROJECT_ROOT / dir_path).resolve()
        if not str(full_path).startswith(str(PROJECT_ROOT.resolve())):
            return {"error": f"Access denied: path outside project root"}
        if not full_path.exists():
            return {"error": f"Directory not found: {dir_path}"}
        items = []
        for item in full_path.iterdir():
            item_type = "dir" if item.is_dir() else "file"
            items.append({"name": item.name, "type": item_type})
        return {"directory": dir_path, "items": items}
    except Exception as e:
        return {"error": str(e)}


def query_api(method: str, path: str, body: dict | None = None) -> dict:
    """
    Call the LMS backend API.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        path: API path (e.g., "/items/", "/analytics/completion-rate?lab=lab-01")
        body: Optional JSON body for POST/PUT requests
    
    Returns:
        dict with "status_code" and "body" (parsed JSON response)
    """
    try:
        url = f"{AGENT_API_BASE_URL.rstrip('/')}{path}"
        headers = {
            "Authorization": f"Bearer {LMS_API_KEY}",
            "Content-Type": "application/json",
        }
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=body or {}, timeout=30)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=body or {}, timeout=30)
        elif method.upper() == "DELETE":
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
        return {"error": str(e)}


# Tool definitions for function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project. Use for reading documentation, source code, configuration files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file (e.g., 'README.md', 'backend/app/main.py')",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in a project directory. Use for exploring project structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dir": {
                        "type": "string",
                        "description": "Relative path to the directory (e.g., 'backend/app', 'docs')",
                        "default": ".",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Call the LMS backend API to get data, check status codes, or test endpoints. Use for questions about database contents, API behavior, status codes, or debugging API errors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method (GET, POST, PUT, DELETE)",
                    },
                    "path": {
                        "type": "string",
                        "description": "API path including query params (e.g., '/items/', '/analytics/completion-rate?lab=lab-01')",
                    },
                    "body": {
                        "type": "object",
                        "description": "Optional JSON body for POST/PUT requests",
                    },
                },
                "required": ["method", "path"],
            },
        },
    },
]

# Tool implementation mapping
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
    "query_api": query_api,
}

SYSTEM_PROMPT = """Ты — ассистент для работы с проектом Learning Management Service.
Ты можешь использовать инструменты для получения информации о проекте.

Доступные инструменты:
- `read_file` — для чтения файлов документации (wiki), исходного кода, конфигураций
- `list_files` — для поиска файлов в структуре проекта  
- `query_api` — для запросов к работающему API бэкенда (получение данных из БД, проверка статус-кодов, отладка ошибок)

Правила выбора инструмента:
- Для вопросов о документации wiki — используй `read_file`
- Для вопросов о структуре проекта или поиске файлов — используй `list_files` или `read_file`
- Для вопросов о данных в БД ("сколько элементов", "какие пользователи") — используй `query_api`
- Для вопросов о статус-кодах API — используй `query_api`
- Для вопросов об ошибках API — сначала используй `query_api` для воспроизведения ошибки, затем `read_file` для чтения исходного кода

Отвечай кратко и по делу. Если используешь инструменты, обязательно укажи их в tool_calls."""


def execute_tool(name: str, arguments: dict) -> dict:
    """Execute a tool by name with the given arguments."""
    if name not in TOOL_FUNCTIONS:
        return {"error": f"Unknown tool: {name}"}
    try:
        return TOOL_FUNCTIONS[name](**arguments)
    except TypeError as e:
        return {"error": f"Invalid arguments for {name}: {e}"}
    except Exception as e:
        return {"error": str(e)}


def run_agent(question: str, max_iterations: int = 10) -> dict:
    """Run the agentic loop with function calling."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    
    tool_calls_log = []
    
    for iteration in range(max_iterations):
        response = call_llm(messages, tools=TOOLS)
        
        # Check if LLM wants to call tools
        if response.get("tool_calls"):
            for tool_call in response["tool_calls"]:
                func = tool_call["function"]
                tool_name = func["name"]
                try:
                    args = json.loads(func["arguments"]) if isinstance(func["arguments"], str) else func["arguments"]
                except (json.JSONDecodeError, TypeError):
                    args = func["arguments"]
                
                result = execute_tool(tool_name, args)
                
                tool_calls_log.append({
                    "tool": tool_name,
                    "args": args,
                    "result": result,
                })
                
                # Add assistant message with tool call
                messages.append({
                    "role": "assistant",
                    "content": response.get("content"),
                    "tool_calls": [tool_call],
                })
                
                # Add tool result
                messages.append({
                    "role": "tool",
                    "content": json.dumps(result, ensure_ascii=False),
                    "tool_call_id": tool_call["id"],
                })
        else:
            # LLM returned final answer
            return {
                "answer": response.get("content", ""),
                "tool_calls": tool_calls_log,
            }
    
    # Max iterations reached
    return {
        "answer": "Max iterations reached. Last response: " + (response.get("content", "") or "No content"),
        "tool_calls": tool_calls_log,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
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
