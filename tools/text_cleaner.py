#!/usr/bin/env python3
"""
text_cleaner.py — ASR 输出预处理：检测并清理尾部重复垃圾文本
"""

import re
from pathlib import Path


def clean_trailing_repeats(text: str, max_repeats: int = 2) -> str:
    """检测并清理尾部重复的短语/句子

    策略：从尾部向前扫描，找到重复 pattern 并截断到 max_repeats 次。
    支持 2-30 字符长度的重复单元。
    """
    if not text:
        return text

    # 尝试不同长度的重复单元（从长到短）
    best_cut = len(text)
    for unit_len in range(30, 1, -1):
        if unit_len > len(text) // 3:
            continue
        unit = text[-unit_len:]
        # 从尾部往前数重复次数
        count = 0
        pos = len(text)
        while pos >= unit_len and text[pos - unit_len:pos] == unit:
            count += 1
            pos -= unit_len
        if count > max_repeats:
            cut_pos = pos + unit_len * max_repeats
            if cut_pos < best_cut:
                best_cut = cut_pos

    return text[:best_cut]


def clean_text(content: str, suffix: str = ".txt") -> str:
    """清理文本内容，去除 ASR 垃圾

    Args:
        content: 原始文本
        suffix: 文件后缀，用于判断解析方式
    """
    # 对 SRT 先提取纯文本
    if suffix == ".srt":
        lines = []
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            if re.match(r'^\d+$', line):
                continue
            if re.match(r'^\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*', line):
                continue
            line = re.sub(r'<[^>]+>', '', line)
            if line:
                lines.append(line)
        text = ''.join(lines)
    else:
        text = content.strip()

    return clean_trailing_repeats(text)
