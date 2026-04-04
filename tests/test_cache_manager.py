"""
tests/test_cache_manager.py — 缓存管理测试（TODO #6）

覆盖：
- clean 命令删除指定 slug 缓存
- clean --all 删除所有缓存
- 转录后自动删除音频选项
- 列出缓存占用
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from cache_manager import clean_cache, clean_all_caches, list_cache_usage, remove_audio_files


def _make_cache(tmp_path, slug="test_up"):
    cache_dir = tmp_path / slug / "transcripts"
    cache_dir.mkdir(parents=True)
    (cache_dir / "sub_0.srt").write_text("字幕内容", encoding="utf-8")
    (cache_dir / "tmp_audio.wav").write_bytes(b"\x00" * 1024)
    return tmp_path


# ── clean_cache ──────────────────────────────────────────────────────────────

def test_CleanCache_RemovesSlugDirectory(tmp_path):
    base = _make_cache(tmp_path)
    clean_cache(base, "test_up")
    assert not (base / "test_up").exists()


def test_CleanCache_DoesNotAffectOtherSlugs(tmp_path):
    base = _make_cache(tmp_path, "slug_a")
    _make_cache(tmp_path, "slug_b")
    clean_cache(base, "slug_a")
    assert not (base / "slug_a").exists()
    assert (base / "slug_b").exists()


def test_CleanCache_HandlesNonexistentSlug(tmp_path):
    # 不应报错
    clean_cache(tmp_path, "nonexistent")


# ── clean_all_caches ─────────────────────────────────────────────────────────

def test_CleanAll_RemovesAllSlugDirectories(tmp_path):
    _make_cache(tmp_path, "slug_a")
    _make_cache(tmp_path, "slug_b")
    clean_all_caches(tmp_path)
    assert not list(tmp_path.iterdir())


# ── list_cache_usage ─────────────────────────────────────────────────────────

def test_ListCacheUsage_ReturnsSlugSizes(tmp_path):
    _make_cache(tmp_path, "slug_a")
    usage = list_cache_usage(tmp_path)
    assert len(usage) == 1
    assert usage[0]["slug"] == "slug_a"
    assert usage[0]["size_bytes"] > 0
    assert usage[0]["file_count"] > 0


def test_ListCacheUsage_ReturnsEmptyForEmptyDir(tmp_path):
    usage = list_cache_usage(tmp_path)
    assert usage == []


def test_ListCacheUsage_HandlesNonexistentDir(tmp_path):
    usage = list_cache_usage(tmp_path / "nonexistent")
    assert usage == []


# ── remove_audio_files ───────────────────────────────────────────────────────

def test_RemoveAudio_DeletesWavFiles(tmp_path):
    base = _make_cache(tmp_path)
    transcript_dir = base / "test_up" / "transcripts"
    removed = remove_audio_files(transcript_dir)
    assert removed == 1
    assert not (transcript_dir / "tmp_audio.wav").exists()
    assert (transcript_dir / "sub_0.srt").exists()


def test_RemoveAudio_DeletesMultipleAudioFormats(tmp_path):
    d = tmp_path / "audio_test"
    d.mkdir()
    (d / "a.wav").write_bytes(b"\x00")
    (d / "b.mp3").write_bytes(b"\x00")
    (d / "c.m4a").write_bytes(b"\x00")
    (d / "d.srt").write_text("keep", encoding="utf-8")
    removed = remove_audio_files(d)
    assert removed == 3
    assert (d / "d.srt").exists()


def test_RemoveAudio_ReturnsZeroWhenNoAudio(tmp_path):
    d = tmp_path / "no_audio"
    d.mkdir()
    (d / "sub.srt").write_text("字幕", encoding="utf-8")
    removed = remove_audio_files(d)
    assert removed == 0
