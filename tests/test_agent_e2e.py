"""End-to-end tests for the system agent.

These tests verify that the agent uses the correct tools for different types of questions.
They require:
1. LLM API access (configured in .env.agent.secret)
2. Running backend API (for data questions)

Run with: uv run pytest tests/test_agent_e2e.py -v
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


# Path to the agent script
AGENT_SCRIPT = Path(__file__).parent.parent / "agent.py"


def run_agent(question: str) -> dict:
    """Run the agent with a question and return the result."""
    env = os.environ.copy()
    # Ensure environment variables are loaded
    env_file = Path(__file__).parent.parent / ".env.agent.secret"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
    
    result = subprocess.run(
        [sys.executable, str(AGENT_SCRIPT), question],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=AGENT_SCRIPT.parent,
        env=env,
    )
    
    if result.returncode != 0:
        pytest.fail(f"Agent exited with code {result.returncode}: {result.stderr}")
    
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        pytest.fail(f"Agent output is not valid JSON: {result.stdout[:200]}")


class TestAgentToolUsage:
    """Tests to verify the agent uses correct tools for different questions."""

    @pytest.mark.e2e
    def test_read_file_for_code_question(self):
        """Question about the backend framework should use read_file tool.
        
        Expected: Agent reads backend/app/main.py or similar to find FastAPI usage.
        """
        question = "What Python web framework does the backend use?"
        result = run_agent(question)
        
        assert "answer" in result, "Missing 'answer' field in result"
        assert "tool_calls" in result, "Missing 'tool_calls' field in result"
        
        # The agent should use read_file to find the framework
        tools_used = {tc.get("tool") for tc in result["tool_calls"]}
        assert "read_file" in tools_used, (
            f"Expected 'read_file' in tool_calls. Tools used: {tools_used}"
        )
        
        # The answer should mention FastAPI
        answer = result["answer"].lower()
        assert "fastapi" in answer, (
            f"Expected 'FastAPI' in answer. Got: {result['answer']}"
        )

    @pytest.mark.e2e
    def test_query_api_for_data_question(self):
        """Question about database items should use query_api tool.
        
        Expected: Agent calls GET /items/ to count items in the database.
        Note: This test requires the backend to be running.
        """
        question = "How many items are in the database?"
        result = run_agent(question)
        
        assert "answer" in result, "Missing 'answer' field in result"
        assert "tool_calls" in result, "Missing 'tool_calls' field in result"
        
        # The agent should use query_api to get data from the database
        tools_used = {tc.get("tool") for tc in result["tool_calls"]}
        assert "query_api" in tools_used, (
            f"Expected 'query_api' in tool_calls. Tools used: {tools_used}"
        )
