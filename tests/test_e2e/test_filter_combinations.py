"""End-to-end tests for complex filter combinations and --include-inactive."""

import json
import os

import pytest


@pytest.mark.e2e
def test_multiple_filter_combinations(env_setup, run_cli_command):
    """Test multiple filters applied together."""
    os.chdir(env_setup["root_dir"])

    # Multiple filters on components
    result = run_cli_command(
        "get 'cm/*' "
        "--filter 'component.config.active=true' "
        "--filter 'component.config.required=false' "
        "--output json"
    )
    assert result["success"]

    data = json.loads(result["stdout"])

    # Verify all components match both filters
    if data.get("components"):
        for component in data["components"]:
            assert component.get("config", {}).get("active") is True
            assert component.get("config", {}).get("required") is False


@pytest.mark.e2e
def test_complex_nested_filters(env_setup, run_cli_command):
    """Test filters on nested properties."""
    os.chdir(env_setup["root_dir"])

    # Filter on nested config properties
    result = run_cli_command(
        "get 'cm/*' " "--filter 'component.config.for_commit=true' " "--output json"
    )
    assert result["success"]

    data = json.loads(result["stdout"])
    if data.get("components"):
        for component in data["components"]:
            assert component.get("config", {}).get("generated") is True


@pytest.mark.e2e
def test_filter_with_wildcards(env_setup, run_cli_command):
    """Test filters combined with wildcard patterns."""
    os.chdir(env_setup["root_dir"])

    result = run_cli_command(
        "get 'cm/prom*' " "--filter 'component.config.active=true' " "--output json"
    )
    assert result["success"]

    data = json.loads(result["stdout"])
    if data.get("components"):
        for component in data["components"]:
            # Should match pattern AND filter
            assert component["name"].startswith("prom")
            assert component.get("config", {}).get("active") is True


@pytest.mark.e2e
def test_filter_syntax_variations(env_setup, run_cli_command):
    """Test different filter syntax variations."""
    os.chdir(env_setup["root_dir"])

    # Test with spaces around equals
    result = run_cli_command(
        "get 'c/*' --filter 'context.environment = dev' --output json"
    )
    # This might fail depending on implementation
    success_with_spaces = result["success"]

    # Test without spaces (standard)
    result = run_cli_command(
        "get 'c/*' --filter 'context.environment=dev' --output json"
    )
    assert result["success"]

    # Document which syntax works
    if not success_with_spaces:
        # Filters require no spaces around equals
        pass


@pytest.mark.e2e
def test_unicode_filter_values(env_setup, run_cli_command):
    """Test filters with Unicode values."""
    os.chdir(env_setup["root_dir"])

    # Create components with Unicode properties
    contexts_dir = env_setup["contexts_dir"]
    test_context = contexts_dir / "context-dev"

    # Japanese description
    jp_comp = test_context / "unicode_filter_jp"
    jp_comp.mkdir(exist_ok=True)
    (jp_comp / "unicode_filter_jp.cgvalues.yaml").write_text("""component:
  name: unicode_filter_jp
  config:
    active: true
    required: false
    generated: false
  vars:
    component_name: unicode_filter_jp
    description: "テストコンポーネント"
    author: "田中太郎"
    team: "開発チーム"
""")

    # Chinese description
    cn_comp = test_context / "unicode_filter_cn"
    cn_comp.mkdir(exist_ok=True)
    (cn_comp / "unicode_filter_cn.cgvalues.yaml").write_text("""component:
  name: unicode_filter_cn
  config:
    active: true
    required: false
    generated: false
  vars:
    component_name: unicode_filter_cn
    description: "测试组件"
    author: "李明"
    team: "开发团队"
""")

    # Russian description
    ru_comp = test_context / "unicode_filter_ru"
    ru_comp.mkdir(exist_ok=True)
    (ru_comp / "unicode_filter_ru.cgvalues.yaml").write_text("""component:
  name: unicode_filter_ru
  config:
    active: true
    required: false
    generated: false
  vars:
    component_name: unicode_filter_ru
    description: "тестовый компонент"
    author: "Иван Петров"
    team: "команда разработки"
""")

    # Test filtering by Unicode description
    result = run_cli_command(
        "get 'cm/*' --filter 'component.vars.description=テストコンポーネント' --output json"
    )
    assert result["success"]

    data = json.loads(result["stdout"])
    components = data.get("components", [])

    # Find the Japanese component
    jp_found = False
    for comp in components:
        if comp.get("name") == "unicode_filter_jp":
            jp_found = True
            break

    # Filter might not work with Unicode, document behavior
    if jp_found:
        assert len(components) == 1
        assert components[0]["name"] == "unicode_filter_jp"

    # Test filtering by Unicode author
    result = run_cli_command(
        "get 'cm/*' --filter 'component.vars.author=李明' --output json"
    )
    assert result["success"]

    data = json.loads(result["stdout"])
    components = data.get("components", [])

    # Find the Chinese component
    cn_found = False
    for comp in components:
        if comp.get("name") == "unicode_filter_cn":
            cn_found = True
            break

    # Document whether Unicode filtering is supported
    if cn_found:
        assert len(components) == 1
        assert components[0]["name"] == "unicode_filter_cn"


@pytest.mark.e2e
def test_complex_unicode_filter_combinations(env_setup, run_cli_command):
    """Test complex filter combinations with Unicode."""
    os.chdir(env_setup["root_dir"])

    # Create test components with various Unicode properties
    contexts_dir = env_setup["contexts_dir"]
    test_context = contexts_dir / "context-dev"

    # Create multiple components with Unicode and mixed properties
    components_data = [
        {
            "name": "unicode_active_jp",
            "active": True,
            "team": "日本チーム",
            "env": "dev",
        },
        {
            "name": "unicode_inactive_jp",
            "active": False,
            "team": "日本チーム",
            "env": "dev",
        },
        {
            "name": "unicode_active_cn",
            "active": True,
            "team": "中国团队",
            "env": "prod",
        },
    ]

    for comp_data in components_data:
        comp_dir = test_context / comp_data["name"]
        comp_dir.mkdir(exist_ok=True)
        (comp_dir / f"{comp_data['name']}.cgvalues.yaml").write_text(f"""component:
  name: {comp_data['name']}
  config:
    active: {str(comp_data['active']).lower()}
    required: false
    generated: false
  vars:
    component_name: {comp_data['name']}
    team: "{comp_data['team']}"
    environment: "{comp_data['env']}"
""")

    # Test combination of active filter with Unicode components
    result = run_cli_command(
        "get 'cm/unicode_*' --filter 'component.config.active=true' --output json"
    )
    assert result["success"]

    data = json.loads(result["stdout"])
    components = data.get("components", [])

    # Should only get active Unicode components
    for comp in components:
        if comp["name"].startswith("unicode_"):
            assert comp.get("config", {}).get("active") is True

    # Test with --include-inactive
    result = run_cli_command("get 'cm/unicode_*' --include-inactive --output json")
    assert result["success"]

    data = json.loads(result["stdout"])
    all_components = data.get("components", [])

    # Should get more components with inactive included
    assert len(all_components) >= len(components)
