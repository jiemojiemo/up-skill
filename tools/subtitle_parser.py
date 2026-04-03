#!/usr/bin/env python3
"""
subtitle_parser.py — 解析字幕文件，输出适合 LLM 分析的整理文本

支持格式：.srt / .vtt / .txt（纯文本逐字稿）
用法：python3 subtitle_parser.py <file_or_dir> [--output <output_file>]
"""

import re
import sys
import os
import argparse
from pathlib import Path


def parse_srt(content: str) -> list[str]:
    """解析 SRT 格式，返回纯文本行列表"""
    lines = []
    # 去掉序号行和时间码行
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r'^\d+$', line):
            continue
        if re.match(r'^\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*', line):
            continue
        # 去掉 HTML 标签（<i>, <b> 等）
        line = re.sub(r'<[^>]+>', '', line)
        if line:
            lines.append(line)
    return lines


def parse_vtt(content: str) -> list[str]:
    """解析 WebVTT 格式，返回纯文本行列表"""
    lines = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('WEBVTT'):
            continue
        if re.match(r'^\d{2}:\d{2}[:\d]*\.\d{3}\s*-->\s*', line):
            continue
        if re.match(r'^NOTE\s', line):
            continue
        # 去掉 VTT 标签
        line = re.sub(r'<[^>]+>', '', line)
        line = re.sub(r'&amp;', '&', line)
        line = re.sub(r'&lt;', '<', line)
        line = re.sub(r'&gt;', '>', line)
        if line:
            lines.append(line)
    return lines


def parse_txt(content: str) -> list[str]:
    """解析纯文本，按行返回非空行"""
    return [line.strip() for line in content.splitlines() if line.strip()]


def merge_lines(lines: list[str], chunk_size: int = 10) -> list[str]:
    """
    将连续短句合并为段落，减少碎片感，便于 LLM 分析。
    每 chunk_size 行合并为一段。
    """
    chunks = []
    for i in range(0, len(lines), chunk_size):
        chunk = ' '.join(lines[i:i + chunk_size])
        chunks.append(chunk)
    return chunks


def parse_file(path: Path) -> str:
    """解析单个字幕文件，返回整理后的文本"""
    content = path.read_text(encoding='utf-8', errors='ignore')
    suffix = path.suffix.lower()

    if suffix == '.srt':
        lines = parse_srt(content)
    elif suffix == '.vtt':
        lines = parse_vtt(content)
    else:
        lines = parse_txt(content)

    # 去重相邻重复行（字幕常见问题）
    deduped = []
    prev = None
    for line in lines:
        if line != prev:
            deduped.append(line)
            prev = line

    chunks = merge_lines(deduped)
    return '\n\n'.join(chunks)


def parse_directory(dir_path: Path) -> str:
    """解析目录下所有字幕文件，按文件名排序合并"""
    results = []
    for ext in ('*.srt', '*.vtt', '*.txt'):
        for f in sorted(dir_path.glob(ext)):
            text = parse_file(f)
            results.append(f'=== {f.name} ===\n{text}')
    return '\n\n'.join(results)


def main():
    parser = argparse.ArgumentParser(description='解析字幕文件为 LLM 可分析文本')
    parser.add_argument('input', help='字幕文件或目录路径')
    parser.add_argument('--output', '-o', help='输出文件路径（默认打印到 stdout）')
    parser.add_argument('--chunk-size', type=int, default=10,
                        help='每段合并的行数（默认 10）')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f'错误：路径不存在 {input_path}', file=sys.stderr)
        sys.exit(1)

    if input_path.is_dir():
        result = parse_directory(input_path)
    else:
        result = parse_file(input_path)

    if args.output:
        Path(args.output).write_text(result, encoding='utf-8')
        print(f'已写入 {args.output}')
    else:
        print(result)


if __name__ == '__main__':
    main()
