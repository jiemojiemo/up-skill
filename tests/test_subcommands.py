"""
tests/test_subcommands.py — 验证子命令已移除，改为自然语言用法

验证：
1. 不存在 /{slug}-brainstorm、/{slug}-script、/{slug}-check 等假子命令
2. SKILL.md、README.md、merger.md 均使用自然语言描述用法
"""

import os
import re

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(relpath: str) -> str:
    with open(os.path.join(PROJECT_ROOT, relpath), encoding="utf-8") as f:
        return f.read()


# ── SKILL.md ─────────────────────────────────────────────────────────────────

class TestSkillMdSubcommands:

    def test_NoCommentSubcommand(self):
        content = _read("SKILL.md")
        assert "/{slug}-comment" not in content

    def test_NoLiveSubcommand(self):
        content = _read("SKILL.md")
        assert "/{slug}-live" not in content

    def test_NoBrandSubcommand(self):
        content = _read("SKILL.md")
        assert "/{slug}-brand" not in content

    def test_NoBrainstormSubcommand(self):
        content = _read("SKILL.md")
        assert "/{slug}-brainstorm" not in content

    def test_NoScriptSubcommand(self):
        content = _read("SKILL.md")
        assert "/{slug}-script" not in content

    def test_NoCheckSubcommand(self):
        content = _read("SKILL.md")
        assert "/{slug}-check" not in content

    def test_NoHyphenatedSubcommands(self):
        """确认不存在任何 /{slug}-xxx 形式的子命令"""
        content = _read("SKILL.md")
        matches = re.findall(r'/{slug}-\w+', content)
        assert matches == [], f"Found unexpected subcommands: {matches}"

    def test_HasNaturalLanguageUsage(self):
        """确认使用自然语言描述用法"""
        content = _read("SKILL.md")
        assert "自然语言" in content


# ── README.md ────────────────────────────────────────────────────────────────

class TestReadmeSubcommands:

    def test_NoCommentInReadme(self):
        content = _read("README.md")
        assert "/{slug}-comment" not in content

    def test_NoLiveInReadme(self):
        content = _read("README.md")
        assert "/{slug}-live" not in content

    def test_NoBrandInReadme(self):
        content = _read("README.md")
        assert "/{slug}-brand" not in content

    def test_NoBrainstormInReadme(self):
        content = _read("README.md")
        assert "/{slug}-brainstorm" not in content

    def test_NoScriptInReadme(self):
        content = _read("README.md")
        assert "/{slug}-script" not in content

    def test_NoCheckInReadme(self):
        content = _read("README.md")
        assert "/{slug}-check" not in content

    def test_NoHyphenatedSubcommandsInReadme(self):
        """确认 README 中不存在任何 /{slug}-xxx 形式的子命令"""
        content = _read("README.md")
        matches = re.findall(r'/{slug}-\w+', content)
        assert matches == [], f"Found unexpected subcommands: {matches}"

    def test_HasUsageExamples(self):
        """README 应该有用法示例"""
        content = _read("README.md")
        assert "/ying_shi_ju_feng" in content


# ── merger.md ────────────────────────────────────────────────────────────────

class TestMergerSubcommands:

    def test_NoCommentInMerger(self):
        content = _read("prompts/merger.md")
        assert "`comment`" not in content

    def test_NoBrandCheckOldName(self):
        """brand-check 应已移除"""
        content = _read("prompts/merger.md")
        assert "brand-check" not in content

    def test_NoBrainstormInMerger(self):
        content = _read("prompts/merger.md")
        assert "`brainstorm`" not in content

    def test_NoScriptInMerger(self):
        content = _read("prompts/merger.md")
        assert "`script`" not in content

    def test_NoCheckInMerger(self):
        content = _read("prompts/merger.md")
        assert "`check`" not in content

    def test_HasNaturalLanguageInMerger(self):
        """merger 模板应使用自然语言描述"""
        content = _read("prompts/merger.md")
        assert "自然语言" in content
