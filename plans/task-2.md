# Task 2 Plan – Documentation Agent

## Goal

Update the CLI agent so it can use tools to inspect the project wiki and answer documentation questions with a source reference.

## Tools

### read_file
Read a file from the repository using a relative path.

- Input: `path` (string)
- Output: file contents as text, or an error message

Security:
- reject path traversal such as `../`
- resolve paths relative to the project root
- ensure the resolved path stays inside the project directory

### list_files
List files and directories in a repository path.

- Input: `path` (string)
- Output: newline-separated directory listing, or an error message

Security:
- reject path traversal such as `../`
- resolve paths relative to the project root
- ensure the resolved path stays inside the project directory

## Tool Schemas

Define both tools as function-calling schemas in the LLM request:
- `read_file(path)`
- `list_files(path)`

The model will be instructed to use `list_files` to discover wiki files first, then `read_file` to inspect relevant documentation.

## Agentic Loop

1. Send the user question, system prompt, and tool schemas to the LLM.
2. If the LLM returns `tool_calls`:
   - execute each tool call
   - append the tool result as a `tool` role message
   - send the updated conversation back to the LLM
3. If the LLM returns a normal text response:
   - treat it as the final answer
   - extract or return the answer and source
   - print JSON output
4. Stop after at most 10 tool calls.

## Output Format

The CLI should return JSON with:

- `answer`: final answer text
- `source`: wiki file path and section anchor
- `tool_calls`: all executed tool calls with tool name, args, and result

## Documentation and Tests

- Update `AGENT.md` to document the two tools, the agentic loop, and the prompt strategy.
- Add two regression tests:
  - merge conflict question should use `read_file`
  - wiki listing question should use `list_files`
