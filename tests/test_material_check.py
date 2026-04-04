"""
tests/test_material_check.py — 素材量下限提醒测试（TODO #4）

覆盖：
- 素材不足时返回警告
- 素材充足时不返回警告
- 边界值（刚好 5 个）
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from material_check import check_material_sufficiency


def test_CheckMaterial_WarnsWhenLessThanFiveFiles(tmp_path):
    for i in range(3):
        (tmp_path / f"sub_{i}.srt").write_text(f"内容{i}", encoding="utf-8")
    result = check_material_sufficiency(tmp_path)
    assert result["sufficient"] is False
    assert "5" in result["message"]


def test_CheckMaterial_NoWarningWhenFiveOrMoreFiles(tmp_path):
    for i in range(5):
        (tmp_path / f"sub_{i}.srt").write_text(f"内容{i}" * 1000, encoding="utf-8")
    result = check_material_sufficiency(tmp_path)
    assert result["sufficient"] is True


def test_CheckMaterial_WarnsWhenTotalDurationTooShort(tmp_path):
    """即使有 5 个文件，内容太少也应该警告"""
    for i in range(5):
        (tmp_path / f"sub_{i}.srt").write_text("短", encoding="utf-8")
    result = check_material_sufficiency(tmp_path)
    assert result["sufficient"] is False


def test_CheckMaterial_HandlesEmptyDirectory(tmp_path):
    result = check_material_sufficiency(tmp_path)
    assert result["sufficient"] is False
    assert result["file_count"] == 0


def test_CheckMaterial_ReturnsFileCount(tmp_path):
    for i in range(3):
        (tmp_path / f"sub_{i}.srt").write_text(f"内容{i}", encoding="utf-8")
    result = check_material_sufficiency(tmp_path)
    assert result["file_count"] == 3


def test_CheckMaterial_ReturnsTotalChars(tmp_path):
    (tmp_path / "a.srt").write_text("一二三四五", encoding="utf-8")
    result = check_material_sufficiency(tmp_path)
    assert result["total_chars"] == 5
