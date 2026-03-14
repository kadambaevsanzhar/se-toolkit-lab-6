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
