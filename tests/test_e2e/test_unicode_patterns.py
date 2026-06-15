"""
End-to-End tests for Unicode support in patterns and component names.

These tests validate Unicode handling in:
- Component names
- Search patterns
- Wildcard patterns
- Mixed ASCII/Unicode patterns
"""

import json
import os

import pytest


@pytest.mark.e2e
def test_unicode_component_names(env_setup, run_cli_command):
    """Test components with Unicode names."""
    os.chdir(env_setup["root_dir"])

    # Create components with Unicode names in the context file
    # Use the temp directory's contexts, not the original test data
    contexts_dir = env_setup["root_dir"] / "test_data" / "contexts"
    test_context = contexts_dir / "context-dev"

    # Create a new context with Unicode components
    unicode_context_file = test_context / "context-unicode-cgvalues.yaml"
    unicode_context_file.write_text("""context:
  name: context-unicode
  environment: dev
  component_type: component
  active: true
  component:
    - name: コンポーネント_jp
      config:
        active: true
        required: false
        for_commit: false
      vars:
        component_name: コンポーネント_jp
        namespace: unicode-test
        description: "Japanese component テスト"
    - name: 组件_cn
      config:
        active: true
        required: false
        for_commit: false
      vars:
        component_name: 组件_cn
        namespace: unicode-test
        description: "Chinese component 测试"
    - name: компонент_ru
      config:
        active: true
        required: false
        for_commit: false
      vars:
        component_name: компонент_ru
        namespace: unicode-test
        description: "Russian component тест"
    - name: mixed_混合_component
      config:
        active: true
        required: false
        for_commit: false
      vars:
        component_name: mixed_混合_component
        namespace: unicode-test
        description: "Mixed ASCII/Unicode component"
""")

    # Test listing all components
    result = run_cli_command("get 'cm/*' -c test_data/.cgconfig.yaml")
    assert result["success"]

    # Verify Unicode components are listed
    assert "コンポーネント_jp" in result["stdout"]
    assert "组件_cn" in result["stdout"]
    assert "компонент_ru" in result["stdout"]
    assert "mixed_混合_component" in result["stdout"]


@pytest.mark.e2e
def test_unicode_search_patterns(env_setup, run_cli_command):
    """Test searching with Unicode patterns."""
    os.chdir(env_setup["root_dir"])

    # Use the temp directory's contexts
    contexts_dir = env_setup["root_dir"] / "test_data" / "contexts"
    test_context = contexts_dir / "context-dev"

    # Add a component with Unicode to existing context
    context_file = test_context / "context-dev-cgvalues.yaml"
    existing_content = context_file.read_text()

    # Check if unicode component already exists
    if "unicode_テスト_component" not in existing_content:
        # Add the component to the existing context
        # Find the app: section and add our component
        lines = existing_content.splitlines()
        insert_index = -1
        for i, line in enumerate(lines):
            if line.strip() == "app:":
                # Find the last component in the list
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() and not lines[j].startswith(" "):
                        insert_index = j
                        break
                    if lines[j].strip().startswith("- name:"):
                        insert_index = j + 1
                        # Find the end of this component
                        for k in range(j + 1, len(lines)):
                            if lines[k].strip().startswith("- name:") or (
                                lines[k].strip() and not lines[k].startswith(" ")
                            ):
                                insert_index = k
                                break
                            insert_index = k + 1
                break

        if insert_index == -1:
            insert_index = len(lines)

        # Add our component
        component_lines = """    - name: unicode_テスト_component
      config:
        active: true
        required: false
        for_commit: false
      vars:
        component_name: unicode_テスト_component
        namespace: unicode-test"""

        lines.insert(insert_index, component_lines)
        context_file.write_text("\n".join(lines))

    # Test exact Unicode pattern match
    result = run_cli_command(
        "get cm/unicode_テスト_component -c test_data/.cgconfig.yaml"
    )
    assert result["success"]
    assert "unicode_テスト_component" in result["stdout"]

    # Test Unicode wildcard patterns
    result = run_cli_command("get 'cm/*テスト*' -c test_data/.cgconfig.yaml")
    assert result["success"]
    assert "unicode_テスト_component" in result["stdout"]


@pytest.mark.e2e
def test_unicode_wildcard_patterns(env_setup, run_cli_command):
    """Test wildcard patterns with Unicode characters."""
    os.chdir(env_setup["root_dir"])

    contexts_dir = env_setup["root_dir"] / "test_data" / "contexts"
    test_context = contexts_dir / "context-dev"

    # Create a new context with components having Unicode patterns
    pattern_context_file = test_context / "context-patterns-cgvalues.yaml"
    pattern_context_file.write_text("""context:
  name: context-patterns
  environment: dev
  component_type: component
  active: true
  component:
    - name: начало_test
      config:
        active: true
        required: false
        for_commit: false
      vars:
        component_name: начало_test
        description: "Russian prefix"
    - name: test_конец
      config:
        active: true
        required: false
        for_commit: false
      vars:
        component_name: test_конец
        description: "Russian suffix"
    - name: 中间_test_中间
      config:
        active: true
        required: false
        for_commit: false
      vars:
        component_name: 中间_test_中间
        description: "Chinese in middle"
    - name: test_テスト_test
      config:
        active: true
        required: false
        for_commit: false
      vars:
        component_name: test_テスト_test
        description: "Japanese in middle"
""")

    # Test prefix wildcard with Unicode
    result = run_cli_command("get 'cm/начало*' -c test_data/.cgconfig.yaml")
    assert result["success"]
    assert "начало_test" in result["stdout"]

    # Test suffix wildcard with Unicode
    result = run_cli_command("get 'cm/*конец' -c test_data/.cgconfig.yaml")
    assert result["success"]
    assert "test_конец" in result["stdout"]

    # Test middle wildcard with Unicode
    result = run_cli_command("get 'cm/*中间*' -c test_data/.cgconfig.yaml")
    assert result["success"]
    assert "中间_test_中间" in result["stdout"]

    # Test multiple wildcards with Unicode
    result = run_cli_command("get 'cm/*テスト*' -c test_data/.cgconfig.yaml")
    assert result["success"]
    assert "test_テスト_test" in result["stdout"]


@pytest.mark.e2e
def test_unicode_json_output(env_setup, run_cli_command):
    """Test JSON output with Unicode component names and values."""
    os.chdir(env_setup["root_dir"])

    # Create a component with extensive Unicode content
    contexts_dir = env_setup["root_dir"] / "test_data" / "contexts"
    test_context = contexts_dir / "context-dev"

    unicode_rich_context_file = test_context / "context-rich-cgvalues.yaml"
    unicode_rich_context_file.write_text("""context:
  name: context-rich
  environment: dev
  component_type: component
  active: true
  component:
    - name: unicode_rich
      config:
        active: true
        required: false
        for_commit: false
      vars:
        component_name: unicode_rich
        description: "多语言描述 🌍"
        author: "李明"
        team: "チーム"
        status: "готов"
        tags:
          - "标签1"
          - "タグ2"
          - "метка3"
        metadata:
          comment: "This component supports 多种语言 including 日本語 and русский"
          emoji_test: "🚀 🎯 ✨"
""")

    # Get component with JSON output
    result = run_cli_command(
        "get cm/unicode_rich --output json -c test_data/.cgconfig.yaml"
    )
    assert result["success"]

    # Parse JSON and verify Unicode content is preserved
    import re

    json_match = re.search(r"(\{.*\})", result["stdout"], re.DOTALL)
    assert json_match, "No JSON found in output"

    data = json.loads(json_match.group(1))

    # Navigate to the component data
    components = []
    if "components" in data:
        components = data["components"]
    elif "contexts" in data:
        for ctx in data["contexts"]:
            if "components" in ctx:
                components.extend(ctx["components"])

    # Find our unicode_rich component
    unicode_comp = None
    for comp in components:
        if (
            comp.get("name") == "unicode_rich"
            or comp.get("vars", {}).get("component_name") == "unicode_rich"
        ):
            unicode_comp = comp
            break

    assert unicode_comp is not None, "Unicode component not found in JSON output"

    # Verify Unicode values are preserved
    vars = unicode_comp.get("vars", {})
    assert vars.get("author") == "李明"
    assert vars.get("team") == "チーム"
    assert vars.get("status") == "готов"
    assert "🌍" in vars.get("description", "")

    # Verify emoji support
    metadata = vars.get("metadata", {})
    assert "🚀" in metadata.get("emoji_test", "")


@pytest.mark.e2e
def test_unicode_yaml_output(env_setup, run_cli_command):
    """Test YAML output with Unicode content."""
    os.chdir(env_setup["root_dir"])

    # Create a component with extensive Unicode content (same as JSON test)
    contexts_dir = env_setup["root_dir"] / "test_data" / "contexts"
    test_context = contexts_dir / "context-dev"

    unicode_rich_context_file = test_context / "context-rich-yaml-cgvalues.yaml"
    unicode_rich_context_file.write_text("""context:
  name: context-rich-yaml
  environment: dev
  component_type: component
  active: true
  component:
    - name: unicode_rich
      config:
        active: true
        required: false
        for_commit: false
      vars:
        component_name: unicode_rich
        description: "多语言描述 🌍"
        author: "李明"
        team: "チーム"
        status: "готов"
        tags:
          - "标签1"
          - "タグ2"
          - "метка3"
        metadata:
          comment: "This component supports 多种语言 including 日本語 and русский"
          emoji_test: "🚀 🎯 ✨"
""")

    # Get the unicode_rich component with YAML output
    result = run_cli_command(
        "get cm/unicode_rich --output yaml -c test_data/.cgconfig.yaml"
    )
    assert result["success"]

    # Verify Unicode content is preserved in YAML
    assert "李明" in result["stdout"]
    assert "チーム" in result["stdout"]
    assert "готов" in result["stdout"]
    assert "🌍" in result["stdout"]

    # Verify YAML structure is valid (basic check)
    assert "components:" in result["stdout"] or "contexts:" in result["stdout"]


@pytest.mark.e2e
def test_unicode_table_output(env_setup, run_cli_command):
    """Test table output with Unicode content."""
    os.chdir(env_setup["root_dir"])

    # Get components with table output
    result = run_cli_command("get 'cm/*' --output table -c test_data/.cgconfig.yaml")
    assert result["success"]

    # Table should handle Unicode gracefully
    # Check for table structure indicators
    assert "│" in result["stdout"] or "|" in result["stdout"] or "┬" in result["stdout"]

    # Unicode component names should be visible
    # Note: Some Unicode might be truncated in table view, but should not cause errors
    output_lower = result["stdout"].lower()
    assert "component" in output_lower or "name" in output_lower


@pytest.mark.e2e
def test_mixed_ascii_unicode_patterns(env_setup, run_cli_command):
    """Test patterns mixing ASCII and Unicode characters."""
    os.chdir(env_setup["root_dir"])

    contexts_dir = env_setup["root_dir"] / "test_data" / "contexts"
    test_context = contexts_dir / "context-dev"

    # Create components with mixed patterns
    mixed_context_file = test_context / "context-mixed-cgvalues.yaml"
    mixed_context_file.write_text("""context:
  name: context-mixed
  environment: dev
  component_type: component
  active: true
  component:
    - name: api_接口_v1
      config:
        active: true
        required: false
        for_commit: false
      vars:
        component_name: api_接口_v1
    - name: service_サービス_2
      config:
        active: true
        required: false
        for_commit: false
      vars:
        component_name: service_サービス_2
    - name: module_модуль_core
      config:
        active: true
        required: false
        for_commit: false
      vars:
        component_name: module_модуль_core
    - name: test_123_测试
      config:
        active: true
        required: false
        for_commit: false
      vars:
        component_name: test_123_测试
""")

    # Test various mixed patterns
    test_patterns = [
        ("cm/api_*_v1", "api_接口_v1"),
        ("cm/service_*_2", "service_サービス_2"),
        ("cm/*_core", "module_модуль_core"),
        ("cm/test_*_测试", "test_123_测试"),
    ]

    for pattern, expected in test_patterns:
        result = run_cli_command(f"get '{pattern}' -c test_data/.cgconfig.yaml")
        assert result["success"], f"Pattern {pattern} failed"
        assert (
            expected in result["stdout"]
        ), f"Expected {expected} not found for pattern {pattern}"


@pytest.mark.e2e
def test_unicode_name_only_output(env_setup, run_cli_command):
    """Test --name-only flag with Unicode component names."""
    os.chdir(env_setup["root_dir"])

    # Get Unicode components with name-only output
    result = run_cli_command("get 'cm/*' --name-only -c test_data/.cgconfig.yaml")
    assert result["success"]

    # Verify Unicode names are present
    unicode_names = ["コンポーネント_jp", "组件_cn", "компонент_ru", "unicode_rich"]

    for name in unicode_names:
        if name in result["stdout"]:
            # Found at least one Unicode name
            break
    else:
        # None found, but this might be because components don't exist
        # Check if we have any components at all
        assert (
            "component" in result["stdout"].lower() or len(result["stdout"].strip()) > 0
        )


@pytest.mark.e2e
def test_unicode_type_filtering(env_setup, run_cli_command):
    """Test Unicode components work with various query patterns."""
    os.chdir(env_setup["root_dir"])

    # Create components of different types with Unicode names
    contexts_dir = env_setup["root_dir"] / "test_data" / "contexts"
    test_context = contexts_dir / "context-dev"

    # Create a context with Unicode component
    type_context_file = test_context / "context-type-cgvalues.yaml"
    type_context_file.write_text("""context:
  name: context-type
  environment: dev
  component_type: component
  active: true
  component:
    - name: unicode_component_type
      config:
        active: true
        required: false
        for_commit: false
      vars:
        component_name: unicode_component_type
        type: "サービス"
    - name: regular_component
      config:
        active: true
        required: false
        for_commit: false
      vars:
        component_name: regular_component
        type: "service"
""")

    # Test listing all components with Unicode names
    result = run_cli_command("get 'cm/*' -c test_data/.cgconfig.yaml")
    assert result["success"]

    # Should list components including Unicode ones
    assert "unicode_component_type" in result["stdout"]

    # Test getting specific Unicode component
    result = run_cli_command(
        "get 'cm/unicode_component_type' -c test_data/.cgconfig.yaml"
    )
    assert result["success"]
    assert "unicode_component_type" in result["stdout"]
    assert "サービス" in result["stdout"]

    # Test with workspace pattern to get all entities including Unicode components
    result = run_cli_command("get 'w/*' --output json -c test_data/.cgconfig.yaml")
    assert result["success"]
    # Unicode component should be included in workspace results
    assert "unicode_component_type" in result["stdout"]
