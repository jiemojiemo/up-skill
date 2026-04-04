"""验证 plugin 目录结构符合 Claude Code plugin 规范。"""

import json
import os
import re

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestPluginStructure:
    """验证 .claude-plugin/ 元数据。"""

    def test_plugin_json_exists(self):
        path = os.path.join(PROJECT_ROOT, ".claude-plugin", "plugin.json")
        assert os.path.isfile(path)

    def test_plugin_json_required_fields(self):
        path = os.path.join(PROJECT_ROOT, ".claude-plugin", "plugin.json")
        data = json.loads(open(path).read())
        for field in ("name", "description", "version", "author"):
            assert field in data, f"plugin.json missing field: {field}"
        assert isinstance(data["author"], dict)
        assert "name" in data["author"]

    def test_plugin_json_name_matches(self):
        path = os.path.join(PROJECT_ROOT, ".claude-plugin", "plugin.json")
        data = json.loads(open(path).read())
        assert data["name"] == "up-skill"

    def test_marketplace_json_exists(self):
        path = os.path.join(PROJECT_ROOT, ".claude-plugin", "marketplace.json")
        assert os.path.isfile(path)

    def test_marketplace_json_references_plugin(self):
        path = os.path.join(PROJECT_ROOT, ".claude-plugin", "marketplace.json")
        data = json.loads(open(path).read())
        assert "plugins" in data
        assert len(data["plugins"]) >= 1
        assert data["plugins"][0]["name"] == "up-skill"


class TestSkillLocation:
    """验证 SKILL.md 位置和内容。"""

    def test_skill_md_in_skills_dir(self):
        path = os.path.join(PROJECT_ROOT, "skills", "up-skill", "SKILL.md")
        assert os.path.isfile(path), "SKILL.md should be at skills/up-skill/SKILL.md"

    def test_no_skill_md_at_root(self):
        path = os.path.join(PROJECT_ROOT, "SKILL.md")
        assert not os.path.exists(path), "SKILL.md should NOT exist at project root"

    def test_skill_md_has_frontmatter(self):
        path = os.path.join(PROJECT_ROOT, "skills", "up-skill", "SKILL.md")
        content = open(path).read()
        assert content.startswith("---"), "SKILL.md should start with YAML frontmatter"
        # Should have closing ---
        parts = content.split("---")
        assert len(parts) >= 3, "SKILL.md frontmatter not properly closed"

    def test_skill_md_uses_plugin_dir(self):
        path = os.path.join(PROJECT_ROOT, "skills", "up-skill", "SKILL.md")
        content = open(path).read()
        assert "${CLAUDE_SKILL_DIR}" not in content, (
            "SKILL.md should use ${CLAUDE_PLUGIN_DIR}, not ${CLAUDE_SKILL_DIR}"
        )
        assert "${CLAUDE_PLUGIN_DIR}" in content

    def test_skill_md_name_is_create_up(self):
        path = os.path.join(PROJECT_ROOT, "skills", "up-skill", "SKILL.md")
        content = open(path).read()
        assert re.search(r"^name:\s*create-up", content, re.MULTILINE)


class TestProjectDocs:
    """验证文档中的项目结构描述已更新。"""

    def test_agents_md_references_plugin_dir(self):
        path = os.path.join(PROJECT_ROOT, "AGENTS.md")
        content = open(path).read()
        assert ".claude-plugin/" in content
        assert "skills/" in content

    def test_readme_has_plugin_install(self):
        path = os.path.join(PROJECT_ROOT, "README.md")
        content = open(path).read()
        assert "plugin install" in content or "plugin-dir" in content

    def test_install_md_has_plugin_install(self):
        path = os.path.join(PROJECT_ROOT, "INSTALL.md")
        content = open(path).read()
        assert "plugin install" in content or "plugin-dir" in content
