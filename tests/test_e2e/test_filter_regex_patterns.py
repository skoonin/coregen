"""End-to-end tests for regex pattern matching in filter operators.

Tests both ~= and =~ operators to ensure regex functionality works correctly.
"""

import json
import os

import pytest


@pytest.mark.e2e
def test_regex_operators_work(env_setup, run_cli_command):
    """Test that both ~= and =~ operators work with regex patterns."""
    os.chdir(env_setup["root_dir"])

    # Test ~= operator with substring match
    result = run_cli_command("get 'cm/*' --filter 'component.name~=prom' --output json")
    assert result["success"], f"Command failed: {result['stderr']}"

    data = json.loads(result["stdout"])
    if data.get("components"):
        for component in data["components"]:
            # Should match any component containing "prom"
            assert "prom" in component["name"].lower()

    # Test =~ operator (should work identically)
    result = run_cli_command("get 'cm/*' --filter 'component.name=~prom' --output json")
    assert result["success"], f"Command failed: {result['stderr']}"

    data2 = json.loads(result["stdout"])
    # Both operators should return the same results
    assert data == data2


@pytest.mark.e2e
def test_regex_basic_functionality(env_setup, run_cli_command):
    """Test basic regex functionality: substring, anchors, and patterns."""
    os.chdir(env_setup["root_dir"])

    # Test substring matching (default)
    result = run_cli_command("get 'cm/*' --filter 'component.name~=prom' --output json")
    assert result["success"]
    data = json.loads(result["stdout"])
    if data.get("components"):
        assert any("prom" in c["name"] for c in data["components"])

    # Test start anchor
    result = run_cli_command(
        "get 'cm/*' --filter 'component.name~=^prometheus' --output json"
    )
    assert result["success"]
    data = json.loads(result["stdout"])
    if data.get("components"):
        for component in data["components"]:
            assert component["name"].startswith("prometheus")

    # Test exact match with both anchors
    result = run_cli_command(
        "get 'cm/*' --filter 'component.name~=^prometheus$' --output json"
    )
    assert result["success"]
    data = json.loads(result["stdout"])
    if data.get("components"):
        for component in data["components"]:
            assert component["name"] == "prometheus"


@pytest.mark.e2e
def test_regex_invalid_pattern_handling(env_setup, run_cli_command):
    """An invalid regex pattern is rejected with a clear error (exit 2) rather
    than silently returning no matches.
    """
    os.chdir(env_setup["root_dir"])

    # Invalid regex pattern (unclosed bracket)
    result = run_cli_command(
        "get 'cm/*' --filter 'component.name~=[unclosed' --output json",
        expected_code=2,
    )
    assert result["success"], f"Expected exit 2 for invalid regex: {result}"
    combined = (result["stdout"] + result["stderr"]).lower()
    assert "regex" in combined, f"Expected a regex error message; got: {combined}"
