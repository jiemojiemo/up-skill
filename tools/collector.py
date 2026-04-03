#!/usr/bin/env python3
"""
collector.py — UP 主数据采集主入口

支持四种模式：
  1. 本地字幕文件/目录
  2. 本地视频文件/目录 → ASR（whisper）
  3. 单个/多个视频链接 → yt-dlp 抓字幕/ASR
  4. UP 主主页 URL → 列出所有视频 → 用户确认数量 → 批量处理

缓存目录：~/.up-skill/cache/{slug}/transcripts/

用法：
  python3 collector.py --slug <slug> --input <path_or_url> [options]
  python3 collector.py --slug <slug> --space <bilibili_space_url> [--limit 20]
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

CACHE_DIR = Path.home() / '.up-skill' / 'cache'


def get_cache_dir(slug: str) -> Path:
    d = CACHE_DIR / slug / 'transcripts'
    d.mkdir(parents=True, exist_ok=True)
    return d


def is_url(s: str) -> bool:
    return s.startswith('http://') or s.startswith('https://')


def is_space_url(url: str) -> bool:
    return 'space.bilibili.com' in url


# ── 模式 1：本地字幕文件 ──────────────────────────────────────────────────────

def collect_from_subtitles(input_path: Path, slug: str) -> list[Path]:
    """直接复制字幕文件到缓存目录"""
    cache = get_cache_dir(slug)
    collected = []
    if input_path.is_dir():
        for ext in ('*.srt', '*.vtt', '*.txt'):
            for f in sorted(input_path.glob(ext)):
                dest = cache / f.name
                dest.write_bytes(f.read_bytes())
                collected.append(dest)
    else:
        dest = cache / input_path.name
        dest.write_bytes(input_path.read_bytes())
        collected.append(dest)
    print(f'✅ 已导入 {len(collected)} 个字幕文件到缓存')
    return collected


# ── 模式 2：本地视频 → ASR ────────────────────────────────────────────────────

def transcribe_with_whisper(video_path: Path, output_dir: Path) -> Optional[Path]:
    """用 whisper 转录视频，输出 .srt 到 output_dir"""
    out_name = video_path.stem + '.srt'
    out_path = output_dir / out_name
    if out_path.exists():
        print(f'  缓存命中，跳过转录：{out_name}')
        return out_path
    print(f'  转录中：{video_path.name} ...')
    try:
        subprocess.run(
            ['whisper', str(video_path), '--output_format', 'srt',
             '--output_dir', str(output_dir), '--language', 'zh'],
            check=True, capture_output=True
        )
        return out_path
    except FileNotFoundError:
        print('❌ 未找到 whisper，请先安装：pip install openai-whisper', file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e:
        print(f'❌ 转录失败：{e}', file=sys.stderr)
        return None


def collect_from_videos(input_path: Path, slug: str) -> list[Path]:
    """本地视频文件/目录 → ASR"""
    cache = get_cache_dir(slug)
    video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm'}
    videos = []
    if input_path.is_dir():
        for f in sorted(input_path.iterdir()):
            if f.suffix.lower() in video_exts:
                videos.append(f)
    else:
        videos = [input_path]

    collected = []
    for v in videos:
        result = transcribe_with_whisper(v, cache)
        if result:
            collected.append(result)
    print(f'✅ 转录完成 {len(collected)}/{len(videos)} 个视频')
    return collected


# ── 模式 3：视频链接 → yt-dlp ─────────────────────────────────────────────────

def download_subtitles(url: str, cache: Path) -> list[Path]:
    """用 yt-dlp 下载字幕，优先官方字幕，没有则自动字幕"""
    print(f'  下载字幕：{url}')
    cmd = [
        'yt-dlp',
        '--write-sub', '--write-auto-sub',
        '--sub-lang', 'zh-Hans,zh,zh-CN',
        '--sub-format', 'srt/vtt/best',
        '--skip-download',
        '--cookies-from-browser', 'chrome',
        '--output', str(cache / '%(id)s.%(ext)s'),
        url
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except FileNotFoundError:
        print('❌ 未找到 yt-dlp，请先安装：brew install yt-dlp', file=sys.stderr)
        return []
    except subprocess.CalledProcessError:
        # 字幕下载失败，尝试下载视频再 ASR
        print('  官方字幕不可用，尝试 ASR ...')
        return download_and_transcribe(url, cache)

    # 收集下载的字幕文件
    return list(cache.glob('*.srt')) + list(cache.glob('*.vtt'))


def download_and_transcribe(url: str, cache: Path) -> list[Path]:
    """下载视频并用 whisper 转录"""
    video_path = cache / 'tmp_video.mp4'
    cmd = ['yt-dlp', '-f', 'bestaudio', '-o', str(video_path), url]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f'❌ 视频下载失败：{e}', file=sys.stderr)
        return []
    result = transcribe_with_whisper(video_path, cache)
    video_path.unlink(missing_ok=True)  # 转录完删除原视频节省空间
    return [result] if result else []


def collect_from_urls(urls: list[str], slug: str) -> list[Path]:
    """批量处理视频链接"""
    cache = get_cache_dir(slug)
    collected = []
    for url in urls:
        results = download_subtitles(url, cache)
        collected.extend(results)
    print(f'✅ 共获取 {len(collected)} 个字幕文件')
    return collected


# ── 模式 4：UP 主主页 → 批量 ──────────────────────────────────────────────────

def list_space_videos(space_url: str) -> list[dict]:
    """列出 UP 主主页的所有视频"""
    print(f'正在获取视频列表：{space_url}')
    cmd = [
        'yt-dlp', '--flat-playlist', '--dump-json',
        '--playlist-end', '500',  # 最多列 500 个
        '--cookies-from-browser', 'chrome',
        space_url
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        print('❌ 未找到 yt-dlp', file=sys.stderr)
        return []
    except subprocess.CalledProcessError as e:
        print(f'❌ 获取视频列表失败：{e}', file=sys.stderr)
        return []

    videos = []
    for line in result.stdout.splitlines():
        try:
            info = json.loads(line)
            videos.append({
                'id': info.get('id', ''),
                'title': info.get('title', ''),
                'url': info.get('url') or f"https://www.bilibili.com/video/{info.get('id', '')}",
                'duration': info.get('duration', 0),
            })
        except json.JSONDecodeError:
            continue
    return videos


def collect_from_space(space_url: str, slug: str, limit: int = 20, yes: bool = False) -> list[Path]:
    """UP 主主页 → 列出视频 → 用户确认 → 批量处理"""
    videos = list_space_videos(space_url)
    if not videos:
        print('未找到视频', file=sys.stderr)
        return []

    total = len(videos)
    print(f'\n找到 {total} 个视频。')

    if yes:
        n = min(limit, total)
        print(f'自动选择最近 {n} 个视频（--yes 模式）')
    else:
        # 交互确认数量
        print(f'建议先处理最近 {min(limit, total)} 个，全部处理可能需要较长时间。')
        print(f'  [1] 最近 {min(20, total)} 个（推荐）')
        print(f'  [2] 最近 {min(50, total)} 个')
        print(f'  [3] 全部（{total} 个）')
        print(f'  [4] 自定义数量')
        try:
            choice = input('请选择 [1]: ').strip() or '1'
        except EOFError:
            choice = '1'

        if choice == '1':
            n = min(20, total)
        elif choice == '2':
            n = min(50, total)
        elif choice == '3':
            n = total
        elif choice == '4':
            try:
                n = int(input(f'输入数量（1-{total}）: ').strip())
            except (EOFError, ValueError):
                n = min(20, total)
            n = max(1, min(n, total))
        else:
            n = min(20, total)

    selected = videos[:n]
    print(f'\n开始处理 {n} 个视频...\n')

    urls = [v['url'] for v in selected]
    return collect_from_urls(urls, slug)


# ── 主入口 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='UP 主数据采集工具')
    parser.add_argument('--slug', required=True, help='UP 主 slug（用于缓存目录命名）')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--input', help='本地字幕文件/视频文件/目录，或单个视频 URL')
    group.add_argument('--urls', nargs='+', help='多个视频 URL')
    group.add_argument('--space', help='B 站 UP 主主页 URL（space.bilibili.com/...）')

    parser.add_argument('--limit', type=int, default=20, help='主页模式默认处理视频数（默认 20）')
    parser.add_argument('--yes', '-y', action='store_true', help='跳过交互确认，直接使用 --limit 数量')
    parser.add_argument('--list-cache', action='store_true', help='列出已缓存的字幕文件')

    args = parser.parse_args()

    if args.list_cache:
        cache = get_cache_dir(args.slug)
        files = list(cache.glob('*'))
        if files:
            print(f'缓存目录：{cache}')
            for f in sorted(files):
                print(f'  {f.name}')
        else:
            print('缓存为空')
        return

    if args.space:
        collect_from_space(args.space, args.slug, args.limit, yes=args.yes)
    elif args.urls:
        collect_from_urls(args.urls, args.slug)
    elif args.input:
        input_path = Path(args.input)
        if is_url(args.input):
            collect_from_urls([args.input], args.slug)
        elif input_path.exists():
            suffix = input_path.suffix.lower() if input_path.is_file() else ''
            video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm'}
            if suffix in video_exts or (input_path.is_dir() and any(
                input_path.glob(f'*{e}') for e in video_exts
            )):
                collect_from_videos(input_path, args.slug)
            else:
                collect_from_subtitles(input_path, args.slug)
        else:
            print(f'❌ 路径不存在：{args.input}', file=sys.stderr)
            sys.exit(1)

    cache = get_cache_dir(args.slug)
    print(f'\n字幕文件已缓存至：{cache}')
    print('下一步：将缓存目录提供给 Claude 进行四层分析')


if __name__ == '__main__':
    main()
