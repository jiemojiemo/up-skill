#!/usr/bin/env python3
"""
material_check.py — 素材量下限检查

检查缓存目录中的素材是否足够生成高质量 Skill。
建议至少 5 个视频 / 30 分钟素材（约 9000 字）。
"""

from pathlib import Path

MIN_FILE_COUNT = 5
MIN_TOTAL_CHARS = 9000  # 约 30 分钟口播内容


def check_material_sufficiency(cache_dir: Path) -> dict:
    """检查素材量是否充足

    Returns:
        dict with keys: sufficient, file_count, total_chars, message
    """
    subtitle_exts = {'.srt', '.vtt', '.txt'}
    files = [f for f in cache_dir.iterdir() if f.suffix.lower() in subtitle_exts] if cache_dir.exists() else []
    file_count = len(files)

    total_chars = 0
    for f in files:
        total_chars += len(f.read_text(encoding='utf-8', errors='ignore'))

    sufficient = file_count >= MIN_FILE_COUNT and total_chars >= MIN_TOTAL_CHARS

    if not sufficient:
        message = f"⚠️ 素材可能不足（当前 {file_count} 个文件，{total_chars} 字）。建议至少 5 个视频 / 30 分钟素材以获得较准确的分身。"
    else:
        message = f"✅ 素材充足（{file_count} 个文件，{total_chars} 字）"

    return {
        "sufficient": sufficient,
        "file_count": file_count,
        "total_chars": total_chars,
        "message": message,
    }
