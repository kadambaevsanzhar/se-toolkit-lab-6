# Task 2 Plan – Documentation Agent

## Tools

We will implement two tools:

### read_file
Reads a file from the repository.

Parameters:
- path (string)

Security:
- reject paths containing "../"
- ensure path stays inside project root

### list_files
Lists files and directories.

Parameters:
- path (string)

Security:
- reject "../"
- only allow paths inside project root


## Agentic loop

1. Send user question + tool schemas to the LLM.
2. If LLM returns tool_calls:
   - execute each tool
   - append tool results as tool messages
   - send conversation back to LLM
3. If LLM returns text answer:
   - extract answer
   - extract source
   - return JSON
4. Stop after 10 tool calls.


## Output format

Return JSON:

{
  "answer": "...",
  "source": "...",
  "tool_calls": [...]
}
