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
    _extract_video_id,
    download_subtitles,
    download_and_transcribe,
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


# ── download_subtitles 缓存命中 ──────────────────────────────────────────────

def test_DownloadSubtitles_SkipsWhenCacheHit(tmp_path):
    """缓存目录已有该 BV 号的字幕文件时，应直接返回，不调用 yt-dlp"""
    cache = tmp_path / "transcripts"
    cache.mkdir()
    # 预置一个 BV 号对应的字幕文件
    cached_file = cache / "BV1abc123.zh-Hans.srt"
    cached_file.write_text("已缓存的字幕", encoding="utf-8")

    url = "https://www.bilibili.com/video/BV1abc123"

    with patch("collector.get_cache_dir", return_value=cache), \
         patch("collector._check_cookies"), \
         patch("subprocess.run") as mock_run:
        result = download_subtitles(url, cache)

    # 不应调用 yt-dlp
    mock_run.assert_not_called()
    # 应返回缓存的文件
    assert len(result) == 1
    assert "BV1abc123" in result[0].name


def test_DownloadSubtitles_DownloadsWhenNoCacheHit(tmp_path):
    """缓存目录没有该 BV 号的字幕时，应正常调用 yt-dlp"""
    cache = tmp_path / "transcripts"
    cache.mkdir()

    url = "https://www.bilibili.com/video/BV1xyz789"

    def fake_ytdlp_run(cmd, **kwargs):
        # 模拟 yt-dlp 下载了一个字幕文件
        (cache / "BV1xyz789.zh-Hans.srt").write_text("新字幕", encoding="utf-8")

    with patch("collector._check_cookies"), \
         patch("subprocess.run", side_effect=fake_ytdlp_run):
        result = download_subtitles(url, cache)

    assert len(result) >= 1


# ── download_and_transcribe 缓存命中 ────────────────────────────────────────

def test_DownloadAndTranscribe_SkipsWhenCacheHit(tmp_path):
    """缓存目录已有该 BV 号的转录文件时，应直接返回，不下载音频"""
    cache = tmp_path / "transcripts"
    cache.mkdir()
    cached_file = cache / "BV1abc123.srt"
    cached_file.write_text("已缓存的转录", encoding="utf-8")

    url = "https://www.bilibili.com/video/BV1abc123"

    with patch("subprocess.run") as mock_run, \
         patch("collector.asr_transcribe") as mock_asr:
        result = download_and_transcribe(url, cache)

    mock_run.assert_not_called()
    mock_asr.assert_not_called()
    assert len(result) == 1
    assert "BV1abc123" in result[0].name


# ── async_download_subtitles 缓存命中 ───────────────────────────────────────

def test_AsyncDownloadSubtitles_SkipsWhenCacheHit(tmp_path):
    """异步版：缓存命中时跳过下载"""
    import asyncio
    from collector import async_download_subtitles

    cache = tmp_path / "transcripts"
    cache.mkdir()
    cached_file = cache / "BV1abc123.zh-Hans.srt"
    cached_file.write_text("已缓存的字幕", encoding="utf-8")

    url = "https://www.bilibili.com/video/BV1abc123"

    async def _run():
        asr_queue = asyncio.Queue()
        with patch("collector._check_cookies"), \
             patch("collector._async_run_ytdlp") as mock_ytdlp:
            result = await async_download_subtitles(url, cache, None, asr_queue)
        mock_ytdlp.assert_not_called()
        return result

    result = asyncio.run(_run())
    assert len(result) == 1
    assert "BV1abc123" in result[0].name
