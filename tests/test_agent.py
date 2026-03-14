"""Regression tests for the system agent tools.

These tests verify that the agent tools are implemented correctly.
Run with: uv run pytest tests/test_agent.py -v

Note: Tests that require LLM API access or running backend are in 
tests/test_agent_e2e.py (end-to-end tests).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


# Path to the agent script
AGENT_SCRIPT = Path(__file__).parent.parent / "agent.py"


class TestAgentToolImplementation:
    """Tests for individual tool implementations."""

    def test_read_file_returns_content(self):
        """Test that read_file tool returns file content."""
        from agent import read_file
        
        result = read_file("README.md")
        
        assert "path" in result
        assert "content" in result
        assert result["path"] == "README.md"
        assert len(result["content"]) > 0

    def test_read_file_not_found(self):
        """Test that read_file returns error for non-existent file."""
        from agent import read_file
        
        result = read_file("nonexistent_file_12345.txt")
        
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_list_files_returns_items(self):
        """Test that list_files tool returns directory contents."""
        from agent import list_files
        
        result = list_files("backend/app")
        
        assert "directory" in result
        assert "items" in result
        assert len(result["items"]) > 0

    def test_query_api_structure(self):
        """Test that query_api returns expected structure (may fail without backend)."""
        from agent import query_api
        
        result = query_api("GET", "/items/")
        
        # Should return either a successful response or an error
        assert isinstance(result, dict)
        # If backend is not running, we expect an error
        # If backend is running, we expect status_code and body
        if "error" in result:
            # Connection error is expected if backend is not running
            assert any(kw in result["error"].lower() for kw in ["connection", "refused", "error"])
        else:
            # Backend is running
            assert "status_code" in result
            assert "body" in result
