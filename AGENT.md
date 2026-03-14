# System Agent Documentation

## Overview

This agent is designed to answer questions about the Learning Management Service project by using tools to read files, explore the project structure, and query the running backend API.

## Architecture

The agent uses a function-calling loop with a large language model (LLM). When given a question, the agent:

1. Sends the question to the LLM along with tool schemas
2. The LLM decides which tool(s) to call and with what arguments
3. The agent executes the tool calls and returns results to the LLM
4. The LLM processes the results and either calls more tools or provides a final answer
5. The loop continues until the LLM returns a final answer or max iterations is reached

## Tools

### `read_file`

Read the contents of a file from the project.

**Parameters:**
- `path` (string, required): Relative path to the file (e.g., `README.md`, `backend/app/main.py`)

**Returns:**
```json
{
  "path": "README.md",
  "content": "... file contents ..."
}
```

**Use cases:**
- Reading documentation from the wiki
- Reading source code to understand implementation details
- Reading configuration files

### `list_files`

List files and directories in a project directory.

**Parameters:**
- `dir` (string, optional): Relative path to the directory (default: `.`)

**Returns:**
```json
{
  "directory": "backend/app",
  "items": [
    {"name": "main.py", "type": "file"},
    {"name": "routers", "type": "dir"}
  ]
}
```

**Use cases:**
- Exploring project structure
- Finding files when you don't know the exact path
- Discovering available modules

### `query_api`

Call the LMS backend API to get data, check status codes, or test endpoints.

**Parameters:**
- `method` (string, required): HTTP method (GET, POST, PUT, DELETE)
- `path` (string, required): API path including query params (e.g., `/items/`, `/analytics/completion-rate?lab=lab-01`)
- `body` (object, optional): JSON body for POST/PUT requests

**Returns:**
```json
{
  "status_code": 200,
  "body": {...}
}
```

**Authentication:**
The tool automatically includes the `LMS_API_KEY` from environment variables in the `Authorization: Bearer <key>` header.

**Use cases:**
- Querying database contents (e.g., "How many items are in the database?")
- Checking API status codes (e.g., "What status code does /items/ return without auth?")
- Debugging API errors by reproducing them
- Getting analytics data

## Environment Variables

The agent reads all configuration from environment variables:

| Variable             | Purpose                              | Source                  | Default                  |
| -------------------- | ------------------------------------ | ----------------------- | ------------------------ |
| `LLM_API_KEY`        | LLM provider API key                 | `.env.agent.secret`     | (required)               |
| `LLM_API_BASE`       | LLM API endpoint URL                 | `.env.agent.secret`     | (required)               |
| `LLM_MODEL`          | Model name                           | `.env.agent.secret`     | (required)               |
| `LMS_API_KEY`        | Backend API key for `query_api` auth | `.env.docker.secret`    | (required)               |
| `AGENT_API_BASE_URL` | Base URL for `query_api`             | Environment or `.env`   | `http://localhost:42002` |

**Important:** There are two distinct API keys:
- `LLM_API_KEY` authenticates with the LLM provider (e.g., Qwen, OpenAI)
- `LMS_API_KEY` authenticates with the backend LMS API

Do not mix them up.

## How the LLM Decides Which Tool to Use

The system prompt guides the LLM to choose the appropriate tool based on the question type:

| Question Type | Example | Expected Tool |
| ------------- | ------- | ------------- |
| Wiki/documentation lookup | "What steps are needed to protect a branch?" | `read_file` |
| SSH connection guide | "How to connect via SSH?" | `read_file` |
| Source code analysis | "What framework does the backend use?" | `read_file` |
| File discovery | "List all API router modules" | `list_files` |
| Database queries | "How many items are in the database?" | `query_api` |
| API status codes | "What status code does /items/ return?" | `query_api` |
| API error diagnosis | "Query /analytics/completion-rate for lab-99" | `query_api`, then `read_file` |
| System architecture | "Explain the request lifecycle" | `read_file` (docker-compose, Dockerfile, main.py) |
| Pipeline analysis | "How does ETL ensure idempotency?" | `read_file` (etl.py) |

## Usage

```bash
# Basic usage
uv run agent.py "Your question here"

# Example: Query the database
uv run agent.py "How many items are in the database?"

# Example: Read source code
uv run agent.py "What Python web framework does the backend use?"

# Example: Debug an API error
uv run agent.py "Query /analytics/completion-rate for lab-99 and explain the error"
```

## Output Format

The agent returns JSON with the answer and a log of tool calls:

```json
{
  "answer": "There are 120 items in the database.",
  "tool_calls": [
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": {"status_code": 200, "body": [...]}
    }
  ]
}
```

## Testing

Run the agent tests:

```bash
# Run all agent tests
uv run pytest tests/test_agent.py -v

# Run tool implementation tests only
uv run pytest tests/test_agent.py::TestAgentToolImplementation -v

# Run tool usage tests (requires backend running)
uv run pytest tests/test_agent.py::TestAgentToolUsage -v
```

## Benchmark Evaluation

Run the local benchmark:

```bash
uv run run_eval.py
```

The benchmark tests 10 questions across all categories:
- Wiki lookups (questions 0-1)
- System facts from source code (questions 2-3)
- Data-dependent API queries (questions 4-5)
- Bug diagnosis (questions 6-7)
- Open-ended reasoning (questions 8-9)

## Lessons Learned

1. **Tool descriptions matter:** The LLM relies heavily on tool descriptions to decide which tool to use. Vague descriptions lead to wrong tool choices. Be specific about when to use each tool.

2. **Environment variable separation:** Keep LLM credentials separate from backend API credentials. The autochecker injects different values, so hardcoding will cause failures.

3. **Handle null content:** When the LLM returns tool calls, the `content` field may be `null` (not missing). Use `(msg.get("content") or "")` instead of `msg.get("content", "")` to handle this correctly.

4. **Max iterations:** Set a reasonable limit (e.g., 10) to prevent infinite loops. The LLM should converge to an answer within a few iterations.

5. **Error messages in tool results:** Return clear error messages from tools so the LLM can understand what went wrong and potentially retry or try a different approach.

6. **File truncation:** For large files, truncate content to avoid overwhelming the LLM context. Include a note that the file was truncated.

7. **Security:** Validate file paths to prevent directory traversal attacks. Ensure paths stay within the project root.

## Final Evaluation Score

| Category | Questions | Passed |
| -------- | --------- | ------ |
| Wiki lookup | 2 | - |
| System facts | 2 | - |
| Data queries | 2 | - |
| Bug diagnosis | 2 | - |
| Reasoning | 2 | - |
| **Total** | **10** | **-** |

*Run `uv run run_eval.py` to see current score.*

## Files Structure

```
.
├── agent.py              # Main agent implementation
├── tests/
│   └── test_agent.py     # Agent regression tests
├── plans/
│   └── task-3.md         # Implementation plan
├── .env.agent.secret     # LLM credentials
├── .env.docker.secret    # Backend API credentials
└── AGENT.md              # This documentation
```
