#!/usr/bin/env python3
"""
asr_engine.py — ASR 多后端引擎（基于 transcribe-kit）

根据硬件自动选择最优 ASR 引擎：
  - Apple Silicon → mlx-whisper
  - NVIDIA GPU    → faster-whisper
  - CPU           → faster-whisper CPU mode

手动覆盖：
  - 环境变量 UP_SKILL_ASR_ENGINE=mlx|faster|whisper|cohere
  - 函数参数 engine="mlx"|"faster"|"whisper"|"cohere"
"""

import asyncio
import os
import platform
import shutil
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Optional


class Hardware(Enum):
    APPLE_SILICON = "apple_silicon"
    NVIDIA = "nvidia"
    CPU = "cpu"


def detect_hardware() -> Hardware:
    """检测当前硬件类型"""
    if platform.machine() == "arm64" and sys.platform == "darwin":
        return Hardware.APPLE_SILICON
    if shutil.which("nvidia-smi"):
        return Hardware.NVIDIA
    return Hardware.CPU


def select_engine(override: Optional[str] = None) -> str:
    """选择 ASR 引擎，返回 "mlx" | "faster" | "whisper" | "cohere"

    优先级：参数 override > 环境变量 > 硬件自动检测
    """
    valid = {"mlx", "faster", "whisper", "cohere"}

    if override and override in valid:
        return override

    env = os.environ.get("UP_SKILL_ASR_ENGINE", "").strip().lower()
    if env in valid:
        return env

    hw = detect_hardware()
    if hw == Hardware.APPLE_SILICON:
        return "mlx"
    return "faster"


def _write_text_to_file(text: str, out_path: Path) -> Path:
    """将转录文本写入文件并返回路径"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return out_path


def _transcribe_mlx(video_path: Path, output_dir: Path, language: str) -> Optional[Path]:
    """mlx-whisper 后端（via transcribe-kit）"""
    out_path = output_dir / (video_path.stem + ".txt")
    print(f"  [mlx-whisper] 转录中：{video_path.name} ...")
    try:
        from transcribe_kit.app import transcribe_mlx_whisper
        text = transcribe_mlx_whisper(
            audio_path=str(video_path),
            language=language,
        )
        return _write_text_to_file(text, out_path)
    except FileNotFoundError:
        print("❌ 未找到 mlx_whisper，请先安装：pip install mlx-whisper", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ mlx-whisper 转录失败：{e}", file=sys.stderr)
        return None


def _transcribe_faster(video_path: Path, output_dir: Path, language: str) -> Optional[Path]:
    """faster-whisper 后端（via transcribe-kit）"""
    out_path = output_dir / (video_path.stem + ".txt")
    print(f"  [faster-whisper] 转录中：{video_path.name} ...")
    try:
        from transcribe_kit.app import transcribe_faster_whisper
        text = transcribe_faster_whisper(
            audio_path=str(video_path),
            language=language,
        )
        return _write_text_to_file(text, out_path)
    except ImportError:
        print("❌ 未找到 faster-whisper，请先安装：pip install faster-whisper", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ faster-whisper 转录失败：{e}", file=sys.stderr)
        return None


def _transcribe_whisper(video_path: Path, output_dir: Path, language: str) -> Optional[Path]:
    """openai-whisper subprocess 后端（fallback，transcribe-kit 不支持）"""
    out_path = output_dir / (video_path.stem + ".txt")
    print(f"  [whisper] 转录中：{video_path.name} ...")
    try:
        subprocess.run(
            ["whisper", str(video_path), "--output_format", "txt",
             "--output_dir", str(output_dir), "--language", language],
            check=True, capture_output=True,
        )
        return out_path
    except FileNotFoundError:
        print("❌ 未找到 whisper，请先安装：pip install openai-whisper", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e:
        print(f"❌ whisper 转录失败：{e}", file=sys.stderr)
        return None


_cohere_processor = None
_cohere_model = None


def _get_cohere_model():
    """懒加载 Cohere ASR 模型，只加载一次"""
    global _cohere_processor, _cohere_model
    if _cohere_processor is None:
        from transcribe_kit.app import build_processor, build_model
        print("  [cohere] 加载模型中（仅首次）...")
        _cohere_processor = build_processor()
        _cohere_model = build_model()
    return _cohere_processor, _cohere_model


def _transcribe_cohere(video_path: Path, output_dir: Path, language: str) -> Optional[Path]:
    """Cohere ASR 后端（via transcribe-kit），模型只加载一次"""
    out_path = output_dir / (video_path.stem + ".txt")
    print(f"  [cohere] 转录中：{video_path.name} ...")
    try:
        from transcribe_kit.app import transcribe_demo
        processor, model = _get_cohere_model()
        text = transcribe_demo(
            processor=processor,
            model=model,
            audio_path=str(video_path),
            language=language,
        )
        return _write_text_to_file(text, out_path)
    except ImportError as e:
        print(f"❌ Cohere ASR 依赖缺失：{e}\n  请安装：uv pip install transformers torch accelerate soundfile librosa", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ Cohere ASR 转录失败：{e}", file=sys.stderr)
        return None


def _format_timestamp(seconds: float) -> str:
    """秒数 → SRT 时间戳 HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


_BACKENDS = {
    "mlx": _transcribe_mlx,
    "faster": _transcribe_faster,
    "whisper": _transcribe_whisper,
    "cohere": _transcribe_cohere,
}


def transcribe(
    video_path: Path,
    output_dir: Path,
    language: str = "zh",
    engine: Optional[str] = None,
) -> Optional[Path]:
    """统一转录接口

    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        language: 语言代码，默认 "zh"
        engine: 手动指定引擎 "mlx"|"faster"|"whisper"|"cohere"，None 则自动选择

    Returns:
        生成的 .txt 文件路径，失败返回 None
    """
    out_path = output_dir / (video_path.stem + ".txt")
    if out_path.exists():
        print(f"  缓存命中，跳过转录：{out_path.name}")
        return out_path

    selected = select_engine(engine)
    backend = _BACKENDS[selected]
    return backend(video_path, output_dir, language)


# ── Async 后端 ────────────────────────────────────────────────────────────────

async def _async_transcribe_mlx(video_path: Path, output_dir: Path, language: str) -> Optional[Path]:
    """mlx-whisper async 后端"""
    return await asyncio.to_thread(_transcribe_mlx, video_path, output_dir, language)


async def _async_transcribe_whisper(video_path: Path, output_dir: Path, language: str) -> Optional[Path]:
    """openai-whisper async subprocess 后端"""
    out_path = output_dir / (video_path.stem + ".txt")
    print(f"  [whisper] 转录中：{video_path.name} ...")
    try:
        proc = await asyncio.create_subprocess_exec(
            "whisper", str(video_path), "--output_format", "txt",
            "--output_dir", str(output_dir), "--language", language,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            print(f"❌ whisper 转录失败：{stderr.decode()}", file=sys.stderr)
            return None
        return out_path
    except FileNotFoundError:
        print("❌ 未找到 whisper，请先安装：pip install openai-whisper", file=sys.stderr)
        return None


_faster_lock = asyncio.Lock()


async def _async_transcribe_faster(video_path: Path, output_dir: Path, language: str) -> Optional[Path]:
    """faster-whisper async 后端，用 to_thread + Lock 包装非线程安全 API"""
    async with _faster_lock:
        return await asyncio.to_thread(_transcribe_faster, video_path, output_dir, language)


async def _async_transcribe_cohere(video_path: Path, output_dir: Path, language: str) -> Optional[Path]:
    """Cohere ASR async 后端"""
    return await asyncio.to_thread(_transcribe_cohere, video_path, output_dir, language)


_ASYNC_BACKENDS = {
    "mlx": _async_transcribe_mlx,
    "faster": _async_transcribe_faster,
    "whisper": _async_transcribe_whisper,
    "cohere": _async_transcribe_cohere,
}


async def async_transcribe(
    video_path: Path,
    output_dir: Path,
    language: str = "zh",
    engine: Optional[str] = None,
) -> Optional[Path]:
    """异步统一转录接口，缓存逻辑与 sync 版一致"""
    out_path = output_dir / (video_path.stem + ".txt")
    if out_path.exists():
        print(f"  缓存命中，跳过转录：{out_path.name}")
        return out_path

    selected = select_engine(engine)
    backend = _ASYNC_BACKENDS[selected]
    return await backend(video_path, output_dir, language)
