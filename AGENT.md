# Agent Architecture

## Overview

This project implements a simple CLI agent that sends a question to an LLM and returns a JSON response.

The agent performs the following steps:

1. Accepts a question as a command line argument.
2. Sends the question to an OpenAI-compatible API.
3. Prints a JSON response to stdout.

## Input

Example usage:

uv run agent.py "What does REST stand for?"

## Output

The program prints exactly one JSON object:

{
  "answer": "Representational State Transfer",
  "tool_calls": []
}

Only valid JSON must be printed to stdout.

## Configuration

The agent reads configuration from environment variables:

- LLM_API_KEY
- LLM_API_BASE
- LLM_MODEL

These variables are usually stored in `.env.agent.secret`.

## Project Structure

agent.py 
plans/task-1.md 
AGENT.md 
tests/

## Testing

Tests verify that:

- `agent.py` runs successfully
- stdout contains valid JSON
- the JSON contains `answer`
- the JSON contains `tool_calls`

## Tools

### read_file
Reads a file from the repository.

Parameters:
- path (string)

Security:
- blocks "../"
- ensures file stays inside project root


### list_files
Lists files in a directory.

Parameters:
- path (string)

Security:
- blocks "../"
- ensures path stays inside project root


## Agentic Loop

1. Send user question and tool schemas to the LLM.
2. If the LLM returns tool_calls:
   - execute the tools
   - append results as tool messages
   - send results back to the LLM.
3. If the LLM returns a text answer:
   - return JSON with answer, source, tool_calls.
4. Stop after 10 tool calls.
