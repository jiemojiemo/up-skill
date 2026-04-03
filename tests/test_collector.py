"""
tests/test_collector.py — collector.py 的单元测试

遵循 unit-test-practices：
- 纯函数部分直接测
- 依赖外部进程（yt-dlp/whisper）的部分用 monkeypatch 注入 fake
- 一个测试一个行为，AAA 结构
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))
from collector import (
    is_url,
    is_space_url,
    get_cache_dir,
    collect_from_subtitles,
)


# ── is_url ────────────────────────────────────────────────────────────────────

def test_IsUrl_ReturnsTrueForHttpsUrl():
    assert is_url("https://www.bilibili.com/video/BV1xxx") is True


def test_IsUrl_ReturnsTrueForHttpUrl():
    assert is_url("http://example.com") is True


def test_IsUrl_ReturnsFalseForLocalPath():
    assert is_url("/Users/foo/bar.srt") is False


def test_IsUrl_ReturnsFalseForRelativePath():
    assert is_url("./subtitles/test.srt") is False


def test_IsUrl_ReturnsFalseForEmptyString():
    assert is_url("") is False


# ── is_space_url ──────────────────────────────────────────────────────────────

def test_IsSpaceUrl_ReturnsTrueForBilibiliSpaceUrl():
    assert is_space_url("https://space.bilibili.com/946974/video") is True


def test_IsSpaceUrl_ReturnsFalseForRegularVideoUrl():
    assert is_space_url("https://www.bilibili.com/video/BV1xxx") is False


def test_IsSpaceUrl_ReturnsFalseForOtherDomain():
    assert is_space_url("https://youtube.com/channel/xxx") is False


# ── get_cache_dir ─────────────────────────────────────────────────────────────

def test_GetCacheDir_ReturnsPathUnderHomeUpSkill():
    result = get_cache_dir("test_slug")
    assert ".up-skill" in str(result)
    assert "test_slug" in str(result)
    assert "transcripts" in str(result)


def test_GetCacheDir_CreatesDirectoryIfNotExists(tmp_path):
    with patch("collector.CACHE_DIR", tmp_path):
        result = get_cache_dir("new_slug")
        assert result.exists()


# ── collect_from_subtitles ────────────────────────────────────────────────────

def test_CollectFromSubtitles_CopiesSingleSrtFile(tmp_path):
    src = tmp_path / "input.srt"
    src.write_text("字幕内容", encoding="utf-8")
    cache_base = tmp_path / "cache"

    with patch("collector.CACHE_DIR", cache_base):
        result = collect_from_subtitles(src, "test_slug")

    assert len(result) == 1
    assert result[0].read_text(encoding="utf-8") == "字幕内容"


def test_CollectFromSubtitles_CollectsAllSubtitleFilesFromDirectory(tmp_path):
    src_dir = tmp_path / "subs"
    src_dir.mkdir()
    (src_dir / "a.srt").write_text("内容A", encoding="utf-8")
    (src_dir / "b.vtt").write_text("内容B", encoding="utf-8")
    (src_dir / "c.txt").write_text("内容C", encoding="utf-8")
    (src_dir / "d.mp4").write_text("视频", encoding="utf-8")  # 不应被收集
    cache_base = tmp_path / "cache"

    with patch("collector.CACHE_DIR", cache_base):
        result = collect_from_subtitles(src_dir, "test_slug")

    assert len(result) == 3


def test_CollectFromSubtitles_IgnoresNonSubtitleFiles(tmp_path):
    src_dir = tmp_path / "mixed"
    src_dir.mkdir()
    (src_dir / "video.mp4").write_text("视频", encoding="utf-8")
    (src_dir / "sub.srt").write_text("字幕", encoding="utf-8")
    cache_base = tmp_path / "cache"

    with patch("collector.CACHE_DIR", cache_base):
        result = collect_from_subtitles(src_dir, "test_slug")

    assert len(result) == 1
    assert result[0].suffix == ".srt"
