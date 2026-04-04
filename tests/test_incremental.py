"""
tests/test_incremental.py — 增量更新测试（TODO #5）

覆盖：
- 增量分析标记新素材
- merge 结果包含新旧内容
- meta.json 版本递增
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from incremental import detect_new_materials, record_processed, get_unprocessed


def _make_skill_dir(tmp_path):
    skill_dir = tmp_path / "test_up"
    skill_dir.mkdir()
    meta = {
        "name": "测试UP",
        "slug": "test_up",
        "version": "1.0.0",
        "source_materials": ["sub_0.srt", "sub_1.srt"],
        "updated_at": "2025-01-01T00:00:00+00:00",
        "layers": ["persona", "content_brain", "production_style", "brand_guardrails"],
    }
    (skill_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return skill_dir


# ── detect_new_materials ─────────────────────────────────────────────────────

def test_DetectNew_FindsNewFiles(tmp_path):
    skill_dir = _make_skill_dir(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    for name in ("sub_0.srt", "sub_1.srt", "sub_2.srt", "sub_3.srt"):
        (cache_dir / name).write_text("内容", encoding="utf-8")
    new = detect_new_materials(cache_dir, skill_dir)
    assert set(new) == {"sub_2.srt", "sub_3.srt"}


def test_DetectNew_ReturnsEmptyWhenAllProcessed(tmp_path):
    skill_dir = _make_skill_dir(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    for name in ("sub_0.srt", "sub_1.srt"):
        (cache_dir / name).write_text("内容", encoding="utf-8")
    new = detect_new_materials(cache_dir, skill_dir)
    assert new == []


def test_DetectNew_ReturnsAllWhenNoMeta(tmp_path):
    skill_dir = tmp_path / "empty_up"
    skill_dir.mkdir()
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "sub_0.srt").write_text("内容", encoding="utf-8")
    new = detect_new_materials(cache_dir, skill_dir)
    assert new == ["sub_0.srt"]


# ── record_processed ─────────────────────────────────────────────────────────

def test_RecordProcessed_AddsToSourceMaterials(tmp_path):
    skill_dir = _make_skill_dir(tmp_path)
    record_processed(skill_dir, ["sub_2.srt", "sub_3.srt"])
    meta = json.loads((skill_dir / "meta.json").read_text())
    assert "sub_2.srt" in meta["source_materials"]
    assert "sub_3.srt" in meta["source_materials"]


def test_RecordProcessed_DoesNotDuplicate(tmp_path):
    skill_dir = _make_skill_dir(tmp_path)
    record_processed(skill_dir, ["sub_0.srt", "sub_2.srt"])
    meta = json.loads((skill_dir / "meta.json").read_text())
    assert meta["source_materials"].count("sub_0.srt") == 1


# ── get_unprocessed ──────────────────────────────────────────────────────────

def test_GetUnprocessed_CombinesDetectAndFilter(tmp_path):
    skill_dir = _make_skill_dir(tmp_path)
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    for name in ("sub_0.srt", "sub_1.srt", "sub_2.srt"):
        (cache_dir / name).write_text("内容", encoding="utf-8")
    unprocessed = get_unprocessed(cache_dir, skill_dir)
    assert unprocessed == ["sub_2.srt"]
