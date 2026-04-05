"""
tests/test_management_skills.py — 独立管理 Skill 的结构测试

验证 skills/ 下的管理 Skill 文件存在且格式正确。
"""

import os
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_skill(name: str) -> str:
    path = os.path.join(PROJECT_ROOT, "skills", name, "SKILL.md")
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── list-ups ─────────────────────────────────────────────────────────────────

def test_ListUpsSkillMdExists():
    path = os.path.join(PROJECT_ROOT, "skills", "list-ups", "SKILL.md")
    assert os.path.isfile(path)


def test_ListUpsSkillMdHasFrontmatter():
    content = _read_skill("list-ups")
    assert content.startswith("---")
    assert re.search(r"^name:\s*list-ups", content, re.MULTILINE)


def test_ListUpsSkillMdIsUserInvocable():
    content = _read_skill("list-ups")
    assert re.search(r"^user-invocable:\s*true", content, re.MULTILINE)


def test_ListUpsSkillMdHasUpsDirPlaceholder():
    content = _read_skill("list-ups")
    assert "{{UPS_DIR}}" in content


# ── update-up ────────────────────────────────────────────────────────────────

def test_UpdateUpSkillMdExists():
    path = os.path.join(PROJECT_ROOT, "skills", "update-up", "SKILL.md")
    assert os.path.isfile(path)


def test_UpdateUpSkillMdHasFrontmatter():
    content = _read_skill("update-up")
    assert content.startswith("---")
    assert re.search(r"^name:\s*update-up", content, re.MULTILINE)


def test_UpdateUpSkillMdIsUserInvocable():
    content = _read_skill("update-up")
    assert re.search(r"^user-invocable:\s*true", content, re.MULTILINE)


# ── delete-up ────────────────────────────────────────────────────────────────

def test_DeleteUpSkillMdExists():
    path = os.path.join(PROJECT_ROOT, "skills", "delete-up", "SKILL.md")
    assert os.path.isfile(path)


def test_DeleteUpSkillMdHasFrontmatter():
    content = _read_skill("delete-up")
    assert content.startswith("---")
    assert re.search(r"^name:\s*delete-up", content, re.MULTILINE)


def test_DeleteUpSkillMdIsUserInvocable():
    content = _read_skill("delete-up")
    assert re.search(r"^user-invocable:\s*true", content, re.MULTILINE)
