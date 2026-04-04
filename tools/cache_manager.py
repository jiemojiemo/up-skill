#!/usr/bin/env python3
"""
cache_manager.py — 缓存管理

支持：
- 清理指定 slug 缓存
- 清理所有缓存
- 列出缓存占用
- 删除音频文件（保留文本）
"""

import shutil
from pathlib import Path

AUDIO_EXTS = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.opus'}


def clean_cache(base_dir: Path, slug: str) -> None:
    """删除指定 slug 的缓存目录"""
    target = base_dir / slug
    if target.exists():
        shutil.rmtree(target)


def clean_all_caches(base_dir: Path) -> None:
    """删除所有缓存目录"""
    if not base_dir.exists():
        return
    for d in list(base_dir.iterdir()):
        if d.is_dir():
            shutil.rmtree(d)


def list_cache_usage(base_dir: Path) -> list[dict]:
    """列出每个 slug 的缓存占用

    Returns:
        [{"slug": str, "size_bytes": int, "file_count": int}, ...]
    """
    if not base_dir.exists():
        return []
    result = []
    for d in sorted(base_dir.iterdir()):
        if not d.is_dir():
            continue
        files = list(d.rglob('*'))
        files = [f for f in files if f.is_file()]
        size = sum(f.stat().st_size for f in files)
        result.append({
            "slug": d.name,
            "size_bytes": size,
            "file_count": len(files),
        })
    return result


def remove_audio_files(directory: Path) -> int:
    """删除目录中的音频文件，返回删除数量"""
    if not directory.exists():
        return 0
    count = 0
    for f in directory.iterdir():
        if f.is_file() and f.suffix.lower() in AUDIO_EXTS:
            f.unlink()
            count += 1
    return count
