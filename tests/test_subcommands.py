"""
tests/test_subcommands.py — 子命令精简的结构测试（TDD）

验证 TODO #4 的三个要求：
1. 删除 /{slug}-comment 和 /{slug}-live
2. -brand 改名为 -check
3. SKILL.md、README.md、merger.md 同步更新
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
        content = _read("skills/up-skill/SKILL.md")
        assert "/{slug}-comment" not in content

    def test_NoLiveSubcommand(self):
        content = _read("skills/up-skill/SKILL.md")
        assert "/{slug}-live" not in content

    def test_NoBrandSubcommand(self):
        content = _read("skills/up-skill/SKILL.md")
        assert "/{slug}-brand" not in content

    def test_HasCheckSubcommand(self):
        content = _read("skills/up-skill/SKILL.md")
        assert "-check" in content

    def test_HasExactlyFourSubcommands(self):
        """确认交付列表只有 4 个子命令"""
        content = _read("skills/up-skill/SKILL.md")
        # 匹配 /{slug} 开头的行
        lines = [l for l in content.splitlines() if re.search(r'/{slug}', l)]
        # 去重（同一个子命令可能出现在列表和详细说明中）
        slugs = set()
        for l in lines:
            m = re.search(r'/{slug}(-\w+)?', l)
            if m:
                slugs.add(m.group(0))
        assert slugs == {"/{slug}", "/{slug}-brainstorm", "/{slug}-script", "/{slug}-check"}

    def test_CheckSectionDescription(self):
        """/{slug}-check 的描述应包含'风格边界'"""
        content = _read("skills/up-skill/SKILL.md")
        assert "风格边界" in content


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

    def test_HasCheckInReadme(self):
        content = _read("README.md")
        assert "/{slug}-check" in content

    def test_ReadmeSaysFourWays(self):
        """README 应该说四种方式，不是六种"""
        content = _read("README.md")
        assert "六" not in content
        assert "四" in content


# ── merger.md ────────────────────────────────────────────────────────────────

class TestMergerSubcommands:

    def test_NoCommentInMerger(self):
        content = _read("prompts/merger.md")
        assert "`comment`" not in content

    def test_NoBrandCheckOldName(self):
        """brand-check 应改为 check"""
        content = _read("prompts/merger.md")
        assert "brand-check" not in content

    def test_HasCheckInMerger(self):
        content = _read("prompts/merger.md")
        assert "check" in content
