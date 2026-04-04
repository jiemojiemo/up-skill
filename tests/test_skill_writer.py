"""
tests/test_skill_writer.py — skill_writer.py 的单元测试

遵循 unit-test-practices：
- AAA 结构，一个测试一个行为
- 命名描述行为
- 用 tmp_path fixture 隔离文件系统，无全局状态
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))
from skill_writer import slugify, create_skill, bump_version, archive_version, list_skills


# ── slugify ───────────────────────────────────────────────────────────────────

def test_Slugify_ChineseNameToPinyin():
    assert slugify("影视飓风") == "ying_shi_ju_feng"


def test_Slugify_ChineseNameWithSpacesToPinyin():
    assert slugify("影视 飓风") == "ying_shi_ju_feng"


def test_Slugify_EnglishConvertsToLowercase():
    assert slugify("TestUP") == "testup"


def test_Slugify_MixedChineseEnglishToPinyin():
    assert slugify("up主(测试)") == "up_zhu_ce_shi"


def test_Slugify_EnglishHandlesContinuousSpaces():
    assert slugify("a  b") == "a_b"


def test_Slugify_TrimsLeadingAndTrailingSpaces():
    assert slugify("  名字  ") == "ming_zi"


def test_Slugify_PureEnglishWithHyphens():
    assert slugify("tim-cook") == "tim_cook"


# ── create_skill ──────────────────────────────────────────────────────────────

def test_CreateSkill_CreatesSlugDirectory(tmp_path):
    create_skill("test_up", "测试UP", tmp_path, {})
    assert (tmp_path / "test_up").is_dir()


def test_CreateSkill_CreatesAllFourLayerFiles(tmp_path):
    create_skill("test_up", "测试UP", tmp_path, {})
    skill_dir = tmp_path / "test_up"
    for layer in ("persona.md", "content_brain.md", "production_style.md", "brand_guardrails.md"):
        assert (skill_dir / layer).exists()


def test_CreateSkill_CreatesMetaJson(tmp_path):
    create_skill("test_up", "测试UP", tmp_path, {})
    assert (tmp_path / "test_up" / "meta.json").exists()


def test_CreateSkill_MetaJsonContainsCorrectName(tmp_path):
    create_skill("test_up", "测试UP", tmp_path, {})
    meta = json.loads((tmp_path / "test_up" / "meta.json").read_text())
    assert meta["name"] == "测试UP"


def test_CreateSkill_MetaJsonContainsCorrectSlug(tmp_path):
    create_skill("test_up", "测试UP", tmp_path, {})
    meta = json.loads((tmp_path / "test_up" / "meta.json").read_text())
    assert meta["slug"] == "test_up"


def test_CreateSkill_MetaJsonInitialVersionIsOnePointZero(tmp_path):
    create_skill("test_up", "测试UP", tmp_path, {})
    meta = json.loads((tmp_path / "test_up" / "meta.json").read_text())
    assert meta["version"] == "1.0.0"


def test_CreateSkill_MetaJsonStoresPlatform(tmp_path):
    create_skill("test_up", "测试UP", tmp_path, {"platform": "B站"})
    meta = json.loads((tmp_path / "test_up" / "meta.json").read_text())
    assert meta["platform"] == "B站"


def test_CreateSkill_DoesNotOverwriteExistingLayerFiles(tmp_path):
    skill_dir = tmp_path / "test_up"
    skill_dir.mkdir()
    persona = skill_dir / "persona.md"
    persona.write_text("已有内容", encoding="utf-8")
    create_skill("test_up", "测试UP", tmp_path, {})
    assert persona.read_text(encoding="utf-8") == "已有内容"


# ── bump_version ──────────────────────────────────────────────────────────────

def test_BumpVersion_IncrementsMinorVersion(tmp_path):
    skill_dir = tmp_path / "test_up"
    skill_dir.mkdir()
    (skill_dir / "meta.json").write_text(
        json.dumps({"version": "1.0.0", "updated_at": "2025-01-01T00:00:00+00:00"}),
        encoding="utf-8"
    )
    new_ver = bump_version(skill_dir)
    assert new_ver == "1.0.1"


def test_BumpVersion_UpdatesMetaJsonVersion(tmp_path):
    skill_dir = tmp_path / "test_up"
    skill_dir.mkdir()
    (skill_dir / "meta.json").write_text(
        json.dumps({"version": "1.0.5", "updated_at": "2025-01-01T00:00:00+00:00"}),
        encoding="utf-8"
    )
    bump_version(skill_dir)
    meta = json.loads((skill_dir / "meta.json").read_text())
    assert meta["version"] == "1.0.6"


def test_BumpVersion_UpdatesUpdatedAt(tmp_path):
    skill_dir = tmp_path / "test_up"
    skill_dir.mkdir()
    original_time = "2020-01-01T00:00:00+00:00"
    (skill_dir / "meta.json").write_text(
        json.dumps({"version": "1.0.0", "updated_at": original_time}),
        encoding="utf-8"
    )
    bump_version(skill_dir)
    meta = json.loads((skill_dir / "meta.json").read_text())
    assert meta["updated_at"] != original_time


def test_BumpVersion_ReturnsFallbackWhenMetaJsonMissing(tmp_path):
    skill_dir = tmp_path / "no_meta"
    skill_dir.mkdir()
    result = bump_version(skill_dir)
    assert result == "1.0.0"


# ── archive_version ───────────────────────────────────────────────────────────

def test_ArchiveVersion_CreatesVersionsDirectory(tmp_path):
    skill_dir = tmp_path / "test_up"
    skill_dir.mkdir()
    (skill_dir / "meta.json").write_text(
        json.dumps({"version": "1.0.0", "updated_at": "2025-01-01T00:00:00+00:00"}),
        encoding="utf-8"
    )
    archive_version(skill_dir)
    assert (skill_dir / ".versions" / "1.0.0").is_dir()


def test_ArchiveVersion_CopiesExistingLayerFiles(tmp_path):
    skill_dir = tmp_path / "test_up"
    skill_dir.mkdir()
    (skill_dir / "meta.json").write_text(
        json.dumps({"version": "1.0.0", "updated_at": "2025-01-01T00:00:00+00:00"}),
        encoding="utf-8"
    )
    (skill_dir / "persona.md").write_text("persona 内容", encoding="utf-8")
    archive_version(skill_dir)
    assert (skill_dir / ".versions" / "1.0.0" / "persona.md").exists()


def test_ArchiveVersion_DoesNotFailWhenOptionalFilesAreMissing(tmp_path):
    skill_dir = tmp_path / "test_up"
    skill_dir.mkdir()
    (skill_dir / "meta.json").write_text(
        json.dumps({"version": "1.0.0", "updated_at": "2025-01-01T00:00:00+00:00"}),
        encoding="utf-8"
    )
    # 只有 meta.json，没有其他文件，不应该报错
    archive_version(skill_dir)
    assert (skill_dir / ".versions" / "1.0.0").is_dir()


# ── list_skills ───────────────────────────────────────────────────────────────

def test_ListSkills_PrintsNothingWhenDirectoryDoesNotExist(tmp_path, capsys):
    list_skills(tmp_path / "nonexistent")
    out = capsys.readouterr().out
    assert "暂无" in out


def test_ListSkills_PrintsSkillNamesWhenSkillsExist(tmp_path, capsys):
    create_skill("test_up", "测试UP", tmp_path, {"platform": "B站"})
    list_skills(tmp_path)
    out = capsys.readouterr().out
    assert "测试UP" in out
