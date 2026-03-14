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

import json
import subprocess


def test_merge_conflict_uses_read_file():
    result = subprocess.run(
        ["uv", "run", "agent.py", "How do you resolve a merge conflict?"],
        capture_output=True,
        text=True,
        check=True,
    )

    data = json.loads(result.stdout)

    assert "tool_calls" in data
    assert isinstance(data["tool_calls"], list)
    assert any(call["tool"] == "read_file" for call in data["tool_calls"])
    assert "source" in data
    assert "wiki/git-workflow.md" in data["source"]


def test_list_wiki_files_uses_list_files():
    result = subprocess.run(
        ["uv", "run", "agent.py", "What files are in the wiki?"],
        capture_output=True,
        text=True,
        check=True,
    )

    data = json.loads(result.stdout)

    assert "tool_calls" in data
    assert isinstance(data["tool_calls"], list)
    assert any(call["tool"] == "list_files" for call in data["tool_calls"])
