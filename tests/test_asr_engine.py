"""
tests/test_asr_engine.py — asr_engine.py 的单元测试

覆盖：
- 硬件检测
- 引擎选择（自动 / 环境变量 / 手动覆盖）
- 统一 transcribe 接口（缓存命中 / 后端分发）
- 各后端错误处理
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
from asr_engine import (
    Hardware,
    detect_hardware,
    select_engine,
    transcribe,
    _format_timestamp,
)


# ── detect_hardware ──────────────────────────────────────────────────────────

def test_DetectHardware_ReturnsAppleSilicon_WhenArm64Darwin():
    with patch("asr_engine.platform") as mock_platform, \
         patch("asr_engine.sys") as mock_sys:
        mock_platform.machine.return_value = "arm64"
        mock_sys.platform = "darwin"
        assert detect_hardware() == Hardware.APPLE_SILICON


def test_DetectHardware_ReturnsNvidia_WhenNvidiaSmiExists():
    with patch("asr_engine.platform") as mock_platform, \
         patch("asr_engine.sys") as mock_sys, \
         patch("asr_engine.shutil") as mock_shutil:
        mock_platform.machine.return_value = "x86_64"
        mock_sys.platform = "linux"
        mock_shutil.which.return_value = "/usr/bin/nvidia-smi"
        assert detect_hardware() == Hardware.NVIDIA


def test_DetectHardware_ReturnsCpu_WhenNoGpu():
    with patch("asr_engine.platform") as mock_platform, \
         patch("asr_engine.sys") as mock_sys, \
         patch("asr_engine.shutil") as mock_shutil:
        mock_platform.machine.return_value = "x86_64"
        mock_sys.platform = "linux"
        mock_shutil.which.return_value = None
        assert detect_hardware() == Hardware.CPU


# ── select_engine ────────────────────────────────────────────────────────────

def test_SelectEngine_ReturnsOverride_WhenValid():
    assert select_engine("whisper") == "whisper"
    assert select_engine("mlx") == "mlx"
    assert select_engine("faster") == "faster"


def test_SelectEngine_IgnoresInvalidOverride():
    with patch("asr_engine.detect_hardware", return_value=Hardware.CPU):
        assert select_engine("invalid") == "faster"


def test_SelectEngine_ReadsEnvVar(monkeypatch):
    monkeypatch.setenv("UP_SKILL_ASR_ENGINE", "whisper")
    assert select_engine() == "whisper"


def test_SelectEngine_OverrideBeatsEnvVar(monkeypatch):
    monkeypatch.setenv("UP_SKILL_ASR_ENGINE", "whisper")
    assert select_engine("mlx") == "mlx"


def test_SelectEngine_ReturnsMlx_ForAppleSilicon():
    with patch("asr_engine.detect_hardware", return_value=Hardware.APPLE_SILICON), \
         patch.dict("os.environ", {}, clear=True):
        assert select_engine() == "mlx"


def test_SelectEngine_ReturnsFaster_ForNvidia():
    with patch("asr_engine.detect_hardware", return_value=Hardware.NVIDIA), \
         patch.dict("os.environ", {}, clear=True):
        assert select_engine() == "faster"


def test_SelectEngine_ReturnsFaster_ForCpu():
    with patch("asr_engine.detect_hardware", return_value=Hardware.CPU), \
         patch.dict("os.environ", {}, clear=True):
        assert select_engine() == "faster"


# ── _format_timestamp ────────────────────────────────────────────────────────

def test_FormatTimestamp_FormatsCorrectly():
    assert _format_timestamp(0) == "00:00:00,000"
    assert _format_timestamp(61.5) == "00:01:01,500"
    assert _format_timestamp(3661.123) == "01:01:01,123"


# ── transcribe (统一接口) ────────────────────────────────────────────────────

def test_Transcribe_ReturnsCachedFile_WhenExists(tmp_path):
    video = tmp_path / "test.mp4"
    video.write_text("fake")
    cached = tmp_path / "test.txt"
    cached.write_text("cached subtitle")

    result = transcribe(video, tmp_path)
    assert result == cached


def test_Transcribe_DispatchesToCorrectBackend(tmp_path):
    video = tmp_path / "test.mp4"
    video.write_text("fake")
    expected = tmp_path / "test.srt"

    mock_mlx = MagicMock(return_value=expected)
    with patch("asr_engine.select_engine", return_value="mlx"), \
         patch.dict("asr_engine._BACKENDS", {"mlx": mock_mlx}):
        result = transcribe(video, tmp_path)
        assert result == expected
        mock_mlx.assert_called_once_with(video, tmp_path, "zh")


def test_Transcribe_PassesEngineToSelectEngine(tmp_path):
    video = tmp_path / "test.mp4"
    video.write_text("fake")

    with patch("asr_engine.select_engine", return_value="faster") as mock_select, \
         patch("asr_engine._transcribe_faster", return_value=None):
        transcribe(video, tmp_path, engine="faster")
        mock_select.assert_called_once_with("faster")


def test_Transcribe_PassesLanguageToBackend(tmp_path):
    video = tmp_path / "test.mp4"
    video.write_text("fake")

    mock_w = MagicMock(return_value=None)
    with patch("asr_engine.select_engine", return_value="whisper"), \
         patch.dict("asr_engine._BACKENDS", {"whisper": mock_w}):
        transcribe(video, tmp_path, language="en")
        mock_w.assert_called_once_with(video, tmp_path, "en")


# ── 输出格式：纯文本 txt ─────────────────────────────────────────────────────

def test_Transcribe_CacheCheckUseTxtExtension(tmp_path):
    """缓存命中应检查 .txt 而非 .srt"""
    video = tmp_path / "test.mp4"
    video.write_text("fake")
    cached_txt = tmp_path / "test.txt"
    cached_txt.write_text("cached text")

    result = transcribe(video, tmp_path)
    assert result == cached_txt


def test_Transcribe_DoesNotCacheHitOnSrt(tmp_path):
    """旧的 .srt 文件不应被当作缓存命中"""
    video = tmp_path / "test.mp4"
    video.write_text("fake")
    old_srt = tmp_path / "test.srt"
    old_srt.write_text("old srt")

    mock_backend = MagicMock(return_value=None)
    with patch("asr_engine.select_engine", return_value="mlx"), \
         patch.dict("asr_engine._BACKENDS", {"mlx": mock_backend}):
        transcribe(video, tmp_path)
    # 应该调用后端，说明没有缓存命中
    mock_backend.assert_called_once()


def test_TranscribeMlx_UsesTxtOutputFormat(tmp_path):
    """mlx-whisper 应使用 --output-format txt"""
    video = tmp_path / "test.mp4"
    video.write_text("fake")

    with patch("asr_engine.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        from asr_engine import _transcribe_mlx
        _transcribe_mlx(video, tmp_path, "zh")

    cmd = mock_run.call_args[0][0]
    assert "txt" in cmd
    assert "srt" not in cmd


def test_TranscribeWhisper_UsesTxtOutputFormat(tmp_path):
    """openai-whisper 应使用 --output_format txt"""
    video = tmp_path / "test.mp4"
    video.write_text("fake")

    with patch("asr_engine.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        from asr_engine import _transcribe_whisper
        _transcribe_whisper(video, tmp_path, "zh")

    cmd = mock_run.call_args[0][0]
    assert "txt" in cmd
    assert "srt" not in cmd


def test_TranscribeFaster_OutputsPlainText(tmp_path):
    """faster-whisper 应输出纯文本，不含时间戳"""
    video = tmp_path / "test.mp4"
    video.write_text("fake")

    mock_model_cls = MagicMock()
    mock_model = MagicMock()
    seg1 = MagicMock(text="你好世界")
    seg2 = MagicMock(text="测试文本")
    mock_model.transcribe.return_value = ([seg1, seg2], None)
    mock_model_cls.return_value = mock_model

    fake_module = MagicMock()
    fake_module.WhisperModel = mock_model_cls

    with patch.dict("sys.modules", {"faster_whisper": fake_module}):
        from asr_engine import _transcribe_faster
        result = _transcribe_faster(video, tmp_path, "zh")

    assert result is not None
    assert result.suffix == ".txt"
    content = result.read_text(encoding="utf-8")
    # 不应包含 SRT 时间戳格式
    assert "-->" not in content
    # 应包含文本内容
    assert "你好世界" in content

def test_TranscribeMlx_ReturnsNone_WhenCommandNotFound(tmp_path):
    video = tmp_path / "test.mp4"
    video.write_text("fake")

    with patch("asr_engine.subprocess.run", side_effect=FileNotFoundError):
        from asr_engine import _transcribe_mlx
        assert _transcribe_mlx(video, tmp_path, "zh") is None


def test_TranscribeWhisper_ReturnsNone_WhenCommandNotFound(tmp_path):
    video = tmp_path / "test.mp4"
    video.write_text("fake")

    with patch("asr_engine.subprocess.run", side_effect=FileNotFoundError):
        from asr_engine import _transcribe_whisper
        assert _transcribe_whisper(video, tmp_path, "zh") is None


def test_TranscribeFaster_ReturnsNone_WhenImportFails(tmp_path):
    video = tmp_path / "test.mp4"
    video.write_text("fake")

    with patch.dict("sys.modules", {"faster_whisper": None}):
        from asr_engine import _transcribe_faster
        assert _transcribe_faster(video, tmp_path, "zh") is None
