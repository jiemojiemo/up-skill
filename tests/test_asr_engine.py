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
    cached = tmp_path / "test.srt"
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


# ── 后端错误处理 ─────────────────────────────────────────────────────────────

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
