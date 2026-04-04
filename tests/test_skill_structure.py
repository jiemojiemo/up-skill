"""验证 skill 目录结构符合 Claude Code skill 规范。"""

import os
import re

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestSkillLocation:
    """验证 SKILL.md 位置和内容。"""

    def test_skill_md_at_root(self):
        path = os.path.join(PROJECT_ROOT, "SKILL.md")
        assert os.path.isfile(path), "SKILL.md should be at project root"

    def test_no_skill_md_in_skills_dir(self):
        path = os.path.join(PROJECT_ROOT, "skills", "up-skill", "SKILL.md")
        assert not os.path.exists(path), "SKILL.md should NOT exist at skills/up-skill/"

    def test_skill_md_has_frontmatter(self):
        path = os.path.join(PROJECT_ROOT, "SKILL.md")
        content = open(path).read()
        assert content.startswith("---"), "SKILL.md should start with YAML frontmatter"
        parts = content.split("---")
        assert len(parts) >= 3, "SKILL.md frontmatter not properly closed"

    def test_skill_md_uses_skill_dir(self):
        path = os.path.join(PROJECT_ROOT, "SKILL.md")
        content = open(path).read()
        assert "${CLAUDE_PLUGIN_DIR}" not in content, (
            "SKILL.md should use ${SKILL_DIR}, not ${CLAUDE_PLUGIN_DIR}"
        )
        assert "${SKILL_DIR}" in content

    def test_skill_md_name_is_create_up(self):
        path = os.path.join(PROJECT_ROOT, "SKILL.md")
        content = open(path).read()
        assert re.search(r"^name:\s*create-up", content, re.MULTILINE)

    def test_no_claude_plugin_dir(self):
        """确认 .claude-plugin/ 目录已删除。"""
        path = os.path.join(PROJECT_ROOT, ".claude-plugin")
        assert not os.path.exists(path), ".claude-plugin/ should be removed"


class TestProjectDocs:
    """验证文档中的项目结构描述已更新。"""

    def test_readme_has_skill_install(self):
        path = os.path.join(PROJECT_ROOT, "README.md")
        content = open(path).read()
        assert "skills/up-skill" in content or "SKILL.md" in content

    def test_pyproject_toml_exists(self):
        path = os.path.join(PROJECT_ROOT, "pyproject.toml")
        assert os.path.isfile(path), "pyproject.toml should exist at project root"
