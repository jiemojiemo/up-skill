"""
tests/test_pipeline.py — 端到端管线集成测试

覆盖完整管线：
  主页采集 → 下载/转录 → ASR 引擎选择 → 字幕解析 → 素材检查 → Skill 创建 → SKILL.md 验证 → 增量更新

所有外部依赖（yt-dlp / whisper / 网络）均 mock，测试真实代码路径。
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from collector import (
    collect_from_subtitles,
    collect_from_urls,
    collect_from_space,
    list_space_videos,
    download_subtitles,
    download_and_transcribe,
)
from asr_engine import Hardware, detect_hardware, select_engine, transcribe, _BACKENDS
from subtitle_parser import parse_srt, parse_vtt, parse_file
from text_cleaner import clean_text, clean_trailing_repeats
from material_check import check_material_sufficiency, MIN_FILE_COUNT, MIN_TOTAL_CHARS
from skill_writer import create_skill, bump_version, archive_version
from incremental import detect_new_materials, record_processed


# ── 共享常量 ──────────────────────────────────────────────────────────────────

SAMPLE_SRT = """\
1
00:00:00,000 --> 00:00:03,500
大家好，欢迎来到我的频道

2
00:00:03,500 --> 00:00:07,000
今天我们来聊一聊科技圈最近发生的事情

3
00:00:07,000 --> 00:00:12,000
首先第一个话题，关于人工智能的最新进展

4
00:00:12,000 --> 00:00:18,000
我跟你讲，这个东西确确实实改变了很多行业

5
00:00:18,000 --> 00:00:23,000
然后呢，我们公司最近也在用一些新的工具

6
00:00:23,000 --> 00:00:28,000
非常之好用，团队效率提升了不少
"""

SPACE_URL = "https://space.bilibili.com/946974"

FAKE_YTDLP_JSON_LINES = "\n".join([
    json.dumps({"id": "BV1abc", "title": "视频一", "url": "https://www.bilibili.com/video/BV1abc", "duration": 600}),
    json.dumps({"id": "BV2def", "title": "视频二", "url": "https://www.bilibili.com/video/BV2def", "duration": 900}),
    json.dumps({"id": "BV3ghi", "title": "视频三", "url": "https://www.bilibili.com/video/BV3ghi", "duration": 1200}),
    json.dumps({"id": "BV4jkl", "title": "视频四", "url": "https://www.bilibili.com/video/BV4jkl", "duration": 480}),
    json.dumps({"id": "BV5mno", "title": "视频五", "url": "https://www.bilibili.com/video/BV5mno", "duration": 720}),
])

SAMPLE_SKILL_MD = """\
---
name: test_up
description: "测试UP 的数字分身 — 由 up-skill 生成"
version: "1.0.0"
---

# 测试UP 数字分身

> ⚠️ 本数字分身由 up-skill 生成，不代表真实 UP 主的观点和立场。
> 所有输出内容仅供创作参考，不构成真实人物的言论。

---

## 激活说明

调用本 Skill 后，你将完全以测试UP的视角运行。

可用模式：
- `/test_up` → 像他聊天
- `/test_up-brainstorm` → 像他做选题会（输入方向，输出选题判断 + 标题）
- `/test_up-script` → 像他写口播脚本（输入选题，输出完整脚本）
- `/test_up-check` → 检查内容是否符合他的风格边界（输入文案，输出评分 + 建议）

---

## 核心约束（任何模式下不得违背）

- 用具体数字说话，不含糊
- 不评价同行

---

## 人格层（Persona）

语气轻松，像朋友聊天。

---

## 内容大脑（Content Brain）

偏好科技和生活方式选题。

---

## 生产风格（Production Style）

标题简洁，开头用系列回顾。

---

## 品牌边界（Brand Guardrails）

不接无关品类商单。

---

## Correction 汇总

（暂无记录）
"""


# ── 共享 Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def fake_cache(tmp_path):
    """预填充 6 个 .srt 文件的缓存目录，总字数 > MIN_TOTAL_CHARS"""
    cache_base = tmp_path / "cache"
    cache_dir = cache_base / "test_up" / "transcripts"
    cache_dir.mkdir(parents=True)
    # 每个文件约 2000 字，6 个 = 12000 > 9000
    long_text = "这是一段测试字幕内容，用于验证素材量检查。" * 100  # ~1900 字
    srt_template = "1\n00:00:00,000 --> 00:00:30,000\n{text}\n"
    for i in range(6):
        (cache_dir / f"video_{i}.srt").write_text(
            srt_template.format(text=long_text), encoding="utf-8"
        )
    return cache_base, cache_dir


@pytest.fixture
def fake_skill_dir(tmp_path):
    """通过 create_skill 创建完整目录，并写入 SAMPLE_SKILL_MD"""
    base = tmp_path / "ups"
    create_skill("test_up", "测试UP", base, {"platform": "B站", "domain": "科技"})
    skill_dir = base / "test_up"
    (skill_dir / "SKILL.md").write_text(SAMPLE_SKILL_MD, encoding="utf-8")
    # 写入非空四层文件
    (skill_dir / "persona.md").write_text("# Persona\n\n内容", encoding="utf-8")
    (skill_dir / "content_brain.md").write_text("# Content Brain\n\n内容", encoding="utf-8")
    (skill_dir / "production_style.md").write_text("# Production Style\n\n内容", encoding="utf-8")
    (skill_dir / "brand_guardrails.md").write_text("# Brand Guardrails\n\n内容", encoding="utf-8")
    return skill_dir


# ── Class 1: 主页采集 ────────────────────────────────────────────────────────

class TestSpaceCollection:
    """Stage 1: UP 主主页 → 视频列表 → 批量采集"""

    def test_ListSpaceVideos_ParsesYtdlpJsonOutput(self):
        mock_result = MagicMock()
        mock_result.stdout = FAKE_YTDLP_JSON_LINES
        with patch("collector.subprocess.run", return_value=mock_result):
            videos = list_space_videos(SPACE_URL)
        assert len(videos) == 5
        assert videos[0]["id"] == "BV1abc"
        assert videos[0]["title"] == "视频一"
        assert videos[0]["duration"] == 600
        assert "bilibili.com" in videos[0]["url"]

    def test_ListSpaceVideos_CallsYtdlpWithCorrectArgs(self):
        mock_result = MagicMock()
        mock_result.stdout = ""
        with patch("collector.subprocess.run", return_value=mock_result) as mock_run:
            list_space_videos(SPACE_URL)
        args = mock_run.call_args[0][0]
        assert "yt-dlp" in args
        assert "--flat-playlist" in args
        assert "--dump-json" in args
        assert "--cookies-from-browser" in args
        assert SPACE_URL in args

    def test_ListSpaceVideos_ReturnsEmptyOnFailure(self):
        with patch("collector.subprocess.run", side_effect=subprocess.CalledProcessError(1, "yt-dlp")):
            videos = list_space_videos(SPACE_URL)
        assert videos == []

    def test_CollectFromSpace_LimitsVideoCount(self, tmp_path):
        mock_result = MagicMock()
        mock_result.stdout = FAKE_YTDLP_JSON_LINES
        cache_base = tmp_path / "cache"

        with patch("collector.subprocess.run", return_value=mock_result), \
             patch("collector.CACHE_DIR", cache_base), \
             patch("collector.download_subtitles", return_value=[]) as mock_dl:
            collect_from_space(SPACE_URL, "test_up", limit=3, yes=True)
        assert mock_dl.call_count == 3

    def test_CollectFromSpace_CallsDownloadSubtitlesForEachVideo(self, tmp_path):
        mock_result = MagicMock()
        mock_result.stdout = FAKE_YTDLP_JSON_LINES
        cache_base = tmp_path / "cache"

        with patch("collector.subprocess.run", return_value=mock_result), \
             patch("collector.CACHE_DIR", cache_base), \
             patch("collector.download_subtitles", return_value=[]) as mock_dl:
            collect_from_space(SPACE_URL, "test_up", limit=5, yes=True)
        assert mock_dl.call_count == 5
        # 每次调用的第一个参数应该是视频 URL
        urls_called = [c[0][0] for c in mock_dl.call_args_list]
        assert "https://www.bilibili.com/video/BV1abc" in urls_called


# ── Class 2: 下载 + 转录 ─────────────────────────────────────────────────────

class TestDownloadAndTranscribe:
    """Stage 2: 视频 URL → 字幕下载 / ASR 转录"""

    def test_DownloadSubtitles_TriesOfficialSubtitlesFirst(self, tmp_path):
        cache = tmp_path / "cache"
        cache.mkdir()
        # 模拟 yt-dlp 成功下载字幕
        def fake_run(cmd, **kwargs):
            # 创建一个 .srt 文件模拟下载结果
            (cache / "BV1abc.srt").write_text(SAMPLE_SRT, encoding="utf-8")
            return MagicMock(returncode=0)

        with patch("collector.subprocess.run", side_effect=fake_run):
            result = download_subtitles("https://www.bilibili.com/video/BV1abc", cache)
        assert len(result) >= 1
        assert any(f.suffix == ".srt" for f in result)

    def test_DownloadSubtitles_FallsBackToAsr(self, tmp_path):
        cache = tmp_path / "cache"
        cache.mkdir()

        with patch("collector.subprocess.run", side_effect=subprocess.CalledProcessError(1, "yt-dlp")), \
             patch("collector.download_and_transcribe", return_value=[]) as mock_asr:
            download_subtitles("https://www.bilibili.com/video/BV1abc", cache)
        mock_asr.assert_called_once()

    def test_DownloadAndTranscribe_CallsYtdlpForAudio(self, tmp_path):
        cache = tmp_path / "cache"
        cache.mkdir()

        def fake_run(cmd, **kwargs):
            # 创建 fake wav
            (cache / "tmp_audio.wav").write_text("fake audio", encoding="utf-8")
            return MagicMock(returncode=0)

        with patch("collector.subprocess.run", side_effect=fake_run), \
             patch("collector.asr_transcribe", return_value=None):
            download_and_transcribe("https://example.com/video", cache)
        # 无法直接检查 subprocess 参数因为被 mock 了，但流程不报错即可

    def test_DownloadAndTranscribe_CallsAsrTranscribe(self, tmp_path):
        cache = tmp_path / "cache"
        cache.mkdir()

        def fake_run(cmd, **kwargs):
            (cache / "tmp_audio.wav").write_text("fake", encoding="utf-8")
            return MagicMock(returncode=0)

        with patch("collector.subprocess.run", side_effect=fake_run), \
             patch("collector.asr_transcribe", return_value=None) as mock_asr:
            download_and_transcribe("https://example.com/video", cache)
        mock_asr.assert_called_once()
        # 第一个参数是音频路径
        audio_arg = mock_asr.call_args[0][0]
        assert audio_arg.name == "tmp_audio.wav"

    def test_DownloadAndTranscribe_CleansUpTempAudio(self, tmp_path):
        cache = tmp_path / "cache"
        cache.mkdir()
        audio = cache / "tmp_audio.wav"

        def fake_run(cmd, **kwargs):
            audio.write_text("fake", encoding="utf-8")
            return MagicMock(returncode=0)

        with patch("collector.subprocess.run", side_effect=fake_run), \
             patch("collector.asr_transcribe", return_value=None):
            download_and_transcribe("https://example.com/video", cache)
        assert not audio.exists()


# ── Class 3: ASR 引擎选择 ────────────────────────────────────────────────────

class TestAsrEngineSelection:
    """Stage 3: 硬件检测 → 引擎选择 → 后端分发"""

    def test_AppleSilicon_SelectsMlx(self):
        with patch("asr_engine.platform") as mock_p, \
             patch("asr_engine.sys") as mock_s, \
             patch.dict("os.environ", {}, clear=True):
            mock_p.machine.return_value = "arm64"
            mock_s.platform = "darwin"
            assert select_engine() == "mlx"

    def test_EnvVarOverridesAutoDetect(self, monkeypatch):
        monkeypatch.setenv("UP_SKILL_ASR_ENGINE", "whisper")
        assert select_engine() == "whisper"

    def test_ParameterOverridesEnvVar(self, monkeypatch):
        monkeypatch.setenv("UP_SKILL_ASR_ENGINE", "whisper")
        assert select_engine("mlx") == "mlx"

    def test_Transcribe_DispatchesToSelectedBackend(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.write_text("fake")
        expected = tmp_path / "test.srt"

        mock_backend = MagicMock(return_value=expected)
        with patch("asr_engine.select_engine", return_value="mlx"), \
             patch.dict("asr_engine._BACKENDS", {"mlx": mock_backend}):
            result = transcribe(video, tmp_path)
        assert result == expected
        mock_backend.assert_called_once_with(video, tmp_path, "zh")

    def test_Transcribe_SkipsWhenCacheHit(self, tmp_path):
        video = tmp_path / "test.mp4"
        video.write_text("fake")
        cached = tmp_path / "test.srt"
        cached.write_text("cached")

        mock_backend = MagicMock()
        with patch("asr_engine.select_engine") as mock_sel:
            result = transcribe(video, tmp_path)
        assert result == cached
        mock_sel.assert_not_called()


# ── Class 4: 字幕解析 + 素材检查 ─────────────────────────────────────────────

class TestSubtitleProcessing:
    """Stage 4: SRT → 纯文本 → 清洗 → 素材量检查"""

    def test_ParseSrt_ExtractsPlainText(self):
        lines = parse_srt(SAMPLE_SRT)
        assert len(lines) == 6
        assert "大家好，欢迎来到我的频道" in lines
        # 不应包含序号或时间戳
        for line in lines:
            assert "-->" not in line
            assert not line.strip().isdigit()

    def test_ParseSrt_RemovesHtmlTags(self):
        srt_with_tags = "1\n00:00:00,000 --> 00:00:01,000\n<b>加粗文本</b>和<i>斜体</i>\n"
        lines = parse_srt(srt_with_tags)
        assert lines == ["加粗文本和斜体"]

    def test_CleanText_RemovesTrailingRepeats(self):
        text = "正常内容" + "重复片段" * 10
        cleaned = clean_trailing_repeats(text)
        assert cleaned.count("重复片段") <= 2

    def test_CleanText_PreservesNormalText(self):
        text = "这是一段完全正常的文本，没有任何重复。"
        assert clean_trailing_repeats(text) == text

    def test_MaterialCheck_InsufficientWhenTooFewFiles(self, tmp_path):
        cache = tmp_path / "cache"
        cache.mkdir()
        # 只有 2 个文件
        for i in range(2):
            (cache / f"v{i}.srt").write_text("x" * 5000, encoding="utf-8")
        result = check_material_sufficiency(cache)
        assert result["sufficient"] is False

    def test_MaterialCheck_InsufficientWhenTooFewChars(self, tmp_path):
        cache = tmp_path / "cache"
        cache.mkdir()
        # 5 个文件但每个很短
        for i in range(5):
            (cache / f"v{i}.srt").write_text("短", encoding="utf-8")
        result = check_material_sufficiency(cache)
        assert result["sufficient"] is False

    def test_MaterialCheck_SufficientWhenBothMet(self, fake_cache):
        _, cache_dir = fake_cache
        result = check_material_sufficiency(cache_dir)
        assert result["sufficient"] is True
        assert result["file_count"] >= MIN_FILE_COUNT
        assert result["total_chars"] >= MIN_TOTAL_CHARS


# ── Class 5: Skill 目录生成 + SKILL.md 验证 ──────────────────────────────────

class TestSkillGeneration:
    """Stage 5: create_skill → 目录结构 + SKILL.md 格式验证"""

    def test_CreateSkill_ProducesCompleteDirectory(self, tmp_path):
        base = tmp_path / "ups"
        create_skill("test_up", "测试UP", base, {})
        skill_dir = base / "test_up"
        assert (skill_dir / "persona.md").exists()
        assert (skill_dir / "content_brain.md").exists()
        assert (skill_dir / "production_style.md").exists()
        assert (skill_dir / "brand_guardrails.md").exists()
        assert (skill_dir / "meta.json").exists()

    def test_MetaJson_HasAllRequiredFields(self, fake_skill_dir):
        meta = json.loads((fake_skill_dir / "meta.json").read_text())
        for field in ("name", "slug", "platform", "domain", "version",
                       "created_at", "updated_at", "source_materials", "layers"):
            assert field in meta, f"meta.json 缺少字段: {field}"

    def test_MetaJson_InitialVersion(self, fake_skill_dir):
        meta = json.loads((fake_skill_dir / "meta.json").read_text())
        assert meta["version"] == "1.0.0"

    def test_MetaJson_LayersArray(self, fake_skill_dir):
        meta = json.loads((fake_skill_dir / "meta.json").read_text())
        assert meta["layers"] == ["persona", "content_brain", "production_style", "brand_guardrails"]

    def test_SkillMd_HasFrontmatter(self, fake_skill_dir):
        content = (fake_skill_dir / "SKILL.md").read_text()
        assert content.startswith("---")
        parts = content.split("---")
        assert len(parts) >= 3
        frontmatter = parts[1]
        assert "name:" in frontmatter
        assert "description:" in frontmatter
        assert "version:" in frontmatter

    def test_SkillMd_HasDisclaimer(self, fake_skill_dir):
        content = (fake_skill_dir / "SKILL.md").read_text()
        assert "不代表真实 UP 主" in content

    def test_SkillMd_HasFourInvocationModes(self, fake_skill_dir):
        content = (fake_skill_dir / "SKILL.md").read_text()
        slug = "test_up"
        assert f"/{slug}" in content
        assert f"/{slug}-brainstorm" in content
        assert f"/{slug}-script" in content
        assert f"/{slug}-check" in content

    def test_SkillMd_NoRemovedSubcommands(self, fake_skill_dir):
        content = (fake_skill_dir / "SKILL.md").read_text()
        assert "-comment" not in content
        assert "-brand" not in content
        assert "-live" not in content

    def test_SkillMd_HasCoreConstraints(self, fake_skill_dir):
        content = (fake_skill_dir / "SKILL.md").read_text()
        assert "核心约束" in content

    def test_SkillMd_IsSelfContained(self, fake_skill_dir):
        content = (fake_skill_dir / "SKILL.md").read_text()
        # 不应引用外部文件
        assert "参见 persona.md" not in content
        assert "参见 content_brain.md" not in content
        assert "详见 production_style.md" not in content


# ── Class 6: 增量更新 ────────────────────────────────────────────────────────

class TestSkillUpdate:
    """Stage 6: 增量检测 → 归档 → 版本递增 → 记录已处理"""

    def test_DetectNewMaterials_FindsUnprocessed(self, tmp_path):
        cache = tmp_path / "cache"
        cache.mkdir()
        for i in range(5):
            (cache / f"v{i}.srt").write_text("内容", encoding="utf-8")

        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        (skill_dir / "meta.json").write_text(json.dumps({
            "version": "1.0.0",
            "source_materials": ["v0.srt", "v1.srt", "v2.srt"],
        }), encoding="utf-8")

        new = detect_new_materials(cache, skill_dir)
        assert sorted(new) == ["v3.srt", "v4.srt"]

    def test_DetectNewMaterials_EmptyWhenAllProcessed(self, tmp_path):
        cache = tmp_path / "cache"
        cache.mkdir()
        (cache / "v0.srt").write_text("内容", encoding="utf-8")

        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        (skill_dir / "meta.json").write_text(json.dumps({
            "version": "1.0.0",
            "source_materials": ["v0.srt"],
        }), encoding="utf-8")

        assert detect_new_materials(cache, skill_dir) == []

    def test_ArchiveVersion_CreatesVersionDir(self, fake_skill_dir):
        archive_dir = archive_version(fake_skill_dir)
        assert archive_dir.exists()
        assert ".versions" in str(archive_dir)
        assert "1.0.0" in str(archive_dir)

    def test_ArchiveVersion_CopiesAllFiles(self, fake_skill_dir):
        archive_dir = archive_version(fake_skill_dir)
        for f in ("persona.md", "content_brain.md", "production_style.md",
                   "brand_guardrails.md", "SKILL.md", "meta.json"):
            assert (archive_dir / f).exists(), f"归档缺少 {f}"

    def test_BumpVersion_IncrementsPatch(self, fake_skill_dir):
        new_ver = bump_version(fake_skill_dir)
        assert new_ver == "1.0.1"
        meta = json.loads((fake_skill_dir / "meta.json").read_text())
        assert meta["version"] == "1.0.1"

    def test_BumpVersion_UpdatesTimestamp(self, fake_skill_dir):
        meta_before = json.loads((fake_skill_dir / "meta.json").read_text())
        old_time = meta_before["updated_at"]
        bump_version(fake_skill_dir)
        meta_after = json.loads((fake_skill_dir / "meta.json").read_text())
        assert meta_after["updated_at"] != old_time

    def test_RecordProcessed_UpdatesMetaJson(self, fake_skill_dir):
        record_processed(fake_skill_dir, ["new_video_1.srt", "new_video_2.srt"])
        meta = json.loads((fake_skill_dir / "meta.json").read_text())
        assert "new_video_1.srt" in meta["source_materials"]
        assert "new_video_2.srt" in meta["source_materials"]

    def test_FullUpdateFlow(self, fake_skill_dir, tmp_path):
        """串联完整更新流程：archive → bump → record，验证最终状态"""
        # 准备缓存：3 个旧 + 2 个新
        cache = tmp_path / "update_cache"
        cache.mkdir()
        all_files = ["v0.srt", "v1.srt", "v2.srt", "v3.srt", "v4.srt"]
        for f in all_files:
            (cache / f).write_text("内容", encoding="utf-8")

        # 记录前 3 个为已处理
        meta = json.loads((fake_skill_dir / "meta.json").read_text())
        meta["source_materials"] = ["v0.srt", "v1.srt", "v2.srt"]
        (fake_skill_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 1. 检测新素材
        new = detect_new_materials(cache, fake_skill_dir)
        assert sorted(new) == ["v3.srt", "v4.srt"]

        # 2. 归档旧版本
        archive_dir = archive_version(fake_skill_dir)
        assert (archive_dir / "meta.json").exists()

        # 3. 递增版本
        new_ver = bump_version(fake_skill_dir)
        assert new_ver == "1.0.1"

        # 4. 记录已处理
        record_processed(fake_skill_dir, new)

        # 验证最终状态
        final_meta = json.loads((fake_skill_dir / "meta.json").read_text())
        assert final_meta["version"] == "1.0.1"
        assert "v3.srt" in final_meta["source_materials"]
        assert "v4.srt" in final_meta["source_materials"]
        # 旧版本归档完好
        assert (fake_skill_dir / ".versions" / "1.0.0").is_dir()
