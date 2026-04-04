#!/usr/bin/env python3
"""
incremental.py — 增量更新支持

通过比对 meta.json 中的 source_materials 与缓存目录，
识别新增素材，支持增量分析而非全量重建。
"""

import json
from pathlib import Path


def detect_new_materials(cache_dir: Path, skill_dir: Path) -> list[str]:
    """检测缓存目录中尚未处理的素材文件名

    Args:
        cache_dir: 字幕缓存目录
        skill_dir: UP 主 Skill 目录（含 meta.json）

    Returns:
        新增文件名列表（排序）
    """
    subtitle_exts = {'.srt', '.vtt', '.txt'}
    all_files = sorted(
        f.name for f in cache_dir.iterdir()
        if f.suffix.lower() in subtitle_exts
    ) if cache_dir.exists() else []

    meta_path = skill_dir / 'meta.json'
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        processed = set(meta.get('source_materials', []))
    else:
        processed = set()

    return [f for f in all_files if f not in processed]


def record_processed(skill_dir: Path, filenames: list[str]) -> None:
    """将已处理的文件名记录到 meta.json 的 source_materials

    Args:
        skill_dir: UP 主 Skill 目录
        filenames: 新处理的文件名列表
    """
    meta_path = skill_dir / 'meta.json'
    if not meta_path.exists():
        return
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    existing = set(meta.get('source_materials', []))
    existing.update(filenames)
    meta['source_materials'] = sorted(existing)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')


def get_unprocessed(cache_dir: Path, skill_dir: Path) -> list[str]:
    """便捷接口：返回未处理的素材文件名列表"""
    return detect_new_materials(cache_dir, skill_dir)
