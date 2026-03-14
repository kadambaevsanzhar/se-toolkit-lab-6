import json
import subprocess
import sys


def test_agent_runs():
    result = subprocess.run(
        [sys.executable, "agent.py", "test question"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    data = json.loads(result.stdout)

    assert "answer" in data
    assert "tool_calls" in data
    assert isinstance(data["tool_calls"], list)
