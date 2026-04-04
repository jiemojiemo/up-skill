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
import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from asr_engine import transcribe as asr_transcribe, async_transcribe as asr_async_transcribe
from cache_manager import clean_cache, clean_all_caches, list_cache_usage, remove_audio_files
from material_check import check_material_sufficiency

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

def collect_from_videos(input_path: Path, slug: str, engine: str | None = None) -> list[Path]:
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
        result = asr_transcribe(v, cache, engine=engine)
        if result:
            collected.append(result)
    print(f'✅ 转录完成 {len(collected)}/{len(videos)} 个视频')
    return collected


# ── 模式 3：视频链接 → yt-dlp ─────────────────────────────────────────────────

def download_subtitles(url: str, cache: Path, engine: str | None = None) -> list[Path]:
    """用 yt-dlp 下载字幕，优先官方字幕，没有则自动字幕"""
    print(f'  下载字幕：{url}')
    existing = set(cache.glob('*.srt')) | set(cache.glob('*.vtt'))
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
        return download_and_transcribe(url, cache, engine=engine)

    # 只看新增的字幕文件
    new_subs = list((set(cache.glob('*.srt')) | set(cache.glob('*.vtt'))) - existing)
    if not new_subs:
        print('  未找到字幕文件，尝试 ASR ...')
        return download_and_transcribe(url, cache, engine=engine)
    return new_subs


def _extract_video_id(url: str) -> str:
    """从 B 站 URL 提取视频 ID（BV 号），fallback 用 URL hash"""
    m = re.search(r'(BV[\w]+)', url)
    if m:
        return m.group(1)
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()[:12]


def download_and_transcribe(url: str, cache: Path, engine: str | None = None) -> list[Path]:
    """下载最低质量音频（16kHz 单声道 wav）并用 ASR 转录"""
    vid = _extract_video_id(url)
    audio_path = cache / f'{vid}.wav'
    cmd = [
        'yt-dlp', '-f', 'worstaudio', '-x', '--audio-format', 'wav',
        '--postprocessor-args', 'ffmpeg:-ar 16000 -ac 1',
        '--cookies-from-browser', 'chrome',
        '-o', str(audio_path), url
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else ''
        print(f'❌ 音频下载失败：{e}\n{stderr}', file=sys.stderr)
        return []
    result = asr_transcribe(audio_path, cache, engine=engine)
    audio_path.unlink(missing_ok=True)
    return [result] if result else []


def collect_from_urls(urls: list[str], slug: str, engine: str | None = None,
                      download_jobs: int = 4, asr_jobs: int = 1) -> list[Path]:
    """批量处理视频链接（内部走 async 管线）"""
    return asyncio.run(async_collect_from_urls(urls, slug, engine=engine,
                                               download_jobs=download_jobs,
                                               asr_jobs=asr_jobs))


# ── Async 管线 ───────────────────────────────────────────────────────────────

_print_lock = asyncio.Lock()


async def _aprint(*args, **kwargs):
    """进度输出加锁，防止多任务交错"""
    async with _print_lock:
        print(*args, **kwargs)


async def _async_run_ytdlp(cmd: list[str]) -> subprocess.CompletedProcess:
    """用 asyncio subprocess 执行 yt-dlp"""
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd, stdout, stderr)
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)


async def async_download_subtitles(
    url: str, cache: Path, engine: str | None, asr_queue: asyncio.Queue,
) -> list[Path]:
    """异步下载字幕，无字幕时将音频下载任务放入 ASR 队列"""
    await _aprint(f'  下载字幕：{url}')
    existing = set(cache.glob('*.srt')) | set(cache.glob('*.vtt'))
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
        await _async_run_ytdlp(cmd)
    except FileNotFoundError:
        await _aprint('❌ 未找到 yt-dlp，请先安装：brew install yt-dlp')
        return []
    except subprocess.CalledProcessError:
        await _aprint('  官方字幕不可用，排队 ASR ...')
        await asr_queue.put((url, cache, engine))
        return []

    new_subs = list((set(cache.glob('*.srt')) | set(cache.glob('*.vtt'))) - existing)
    if not new_subs:
        await _aprint('  未找到字幕文件，排队 ASR ...')
        await asr_queue.put((url, cache, engine))
        return []
    return new_subs


async def async_download_and_transcribe(
    url: str, cache: Path, engine: str | None,
) -> list[Path]:
    """异步下载音频并 ASR 转录"""
    vid = _extract_video_id(url)
    audio_path = cache / f'{vid}.wav'
    cmd = [
        'yt-dlp', '-f', 'worstaudio', '-x', '--audio-format', 'wav',
        '--postprocessor-args', 'ffmpeg:-ar 16000 -ac 1',
        '--cookies-from-browser', 'chrome',
        '-o', str(audio_path), url
    ]
    try:
        await _async_run_ytdlp(cmd)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode() if e.stderr else ''
        await _aprint(f'❌ 音频下载失败：{e}\n{stderr}')
        return []
    result = await asr_async_transcribe(audio_path, cache, engine=engine)
    audio_path.unlink(missing_ok=True)
    return [result] if result else []


async def async_collect_from_urls(
    urls: list[str], slug: str, engine: str | None = None,
    download_jobs: int = 4, asr_jobs: int = 1,
) -> list[Path]:
    """异步管线主函数：download_semaphore → Queue → asr consumer"""
    cache = get_cache_dir(slug)
    download_sem = asyncio.Semaphore(download_jobs)
    asr_sem = asyncio.Semaphore(asr_jobs)
    asr_queue: asyncio.Queue = asyncio.Queue(maxsize=asr_jobs * 2)
    collected: list[Path] = []
    total = len(urls)
    done_count = 0
    done_lock = asyncio.Lock()

    async def _bump():
        nonlocal done_count
        async with done_lock:
            done_count += 1
            return done_count

    async def download_one(url: str):
        async with download_sem:
            try:
                results = await async_download_subtitles(url, cache, engine, asr_queue)
                if results:
                    collected.extend(results)
                    n = await _bump()
                    await _aprint(f'[{n}/{total}] 字幕完成，累计 {len(collected)} 个文件')
            except Exception as e:
                await _aprint(f'❌ 下载失败 {url}：{e}')

    async def asr_consumer():
        while True:
            item = await asr_queue.get()
            if item is None:
                asr_queue.task_done()
                break
            url, c, eng = item
            async with asr_sem:
                try:
                    results = await async_download_and_transcribe(url, c, eng)
                    if results:
                        collected.extend(results)
                        n = await _bump()
                        await _aprint(f'[{n}/{total}] ASR 完成，累计 {len(collected)} 个文件')
                except Exception as e:
                    await _aprint(f'❌ ASR 失败 {url}：{e}')
            asr_queue.task_done()

    # 启动 ASR consumer
    consumers = [asyncio.create_task(asr_consumer()) for _ in range(asr_jobs)]

    # 并发下载
    download_tasks = [asyncio.create_task(download_one(url)) for url in urls]
    await asyncio.gather(*download_tasks)

    # 等待 ASR 队列排空，然后发送停止信号
    await asr_queue.join()
    for _ in consumers:
        await asr_queue.put(None)
    await asyncio.gather(*consumers)

    print(f'\n✅ 共获取 {len(collected)} 个字幕文件')
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


def collect_from_space(space_url: str, slug: str, limit: int = 20, yes: bool = False,
                       engine: str | None = None, download_jobs: int = 4,
                       asr_jobs: int = 1) -> list[Path]:
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
    return collect_from_urls(urls, slug, engine=engine,
                             download_jobs=download_jobs, asr_jobs=asr_jobs)


# ── 主入口 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='UP 主数据采集工具')
    parser.add_argument('--slug', required=True, help='UP 主 slug（用于缓存目录命名）')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--input', help='本地字幕文件/视频文件/目录，或单个视频 URL')
    group.add_argument('--urls', nargs='+', help='多个视频 URL')
    group.add_argument('--space', help='B 站 UP 主主页 URL（space.bilibili.com/...）')

    parser.add_argument('--limit', type=int, default=20, help='主页模式默认处理视频数（默认 20）')
    parser.add_argument('--engine', choices=['mlx', 'faster', 'whisper'], help='手动指定 ASR 引擎')
    parser.add_argument('--yes', '-y', action='store_true', help='跳过交互确认，直接使用 --limit 数量')
    parser.add_argument('--list-cache', action='store_true', help='列出已缓存的字幕文件')
    parser.add_argument('--clean', action='store_true', help='清理指定 slug 的缓存')
    parser.add_argument('--clean-all', action='store_true', help='清理所有缓存')
    parser.add_argument('--clean-audio', action='store_true', help='删除缓存中的音频文件，保留文本')
    parser.add_argument('--download-jobs', type=int, default=4, help='下载并发数（默认 4）')
    parser.add_argument('--asr-jobs', type=int, default=1, help='ASR 并发数（默认 1）')

    args = parser.parse_args()

    if args.clean_all:
        clean_all_caches(CACHE_DIR)
        print('✅ 已清理所有缓存')
        return

    if args.clean:
        clean_cache(CACHE_DIR, args.slug)
        print(f'✅ 已清理 {args.slug} 的缓存')
        return

    if args.clean_audio:
        cache = get_cache_dir(args.slug)
        n = remove_audio_files(cache)
        print(f'✅ 已删除 {n} 个音频文件')
        return

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

    if not args.space and not args.urls and not args.input:
        parser.error('请指定 --input、--urls 或 --space 之一')

    if args.space:
        collect_from_space(args.space, args.slug, args.limit, yes=args.yes,
                           engine=args.engine, download_jobs=args.download_jobs,
                           asr_jobs=args.asr_jobs)
    elif args.urls:
        collect_from_urls(args.urls, args.slug, engine=args.engine,
                          download_jobs=args.download_jobs, asr_jobs=args.asr_jobs)
    elif args.input:
        input_path = Path(args.input)
        if is_url(args.input):
            collect_from_urls([args.input], args.slug, engine=args.engine,
                              download_jobs=args.download_jobs, asr_jobs=args.asr_jobs)
        elif input_path.exists():
            suffix = input_path.suffix.lower() if input_path.is_file() else ''
            video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm'}
            if suffix in video_exts or (input_path.is_dir() and any(
                input_path.glob(f'*{e}') for e in video_exts
            )):
                collect_from_videos(input_path, args.slug, engine=args.engine)
            else:
                collect_from_subtitles(input_path, args.slug)
        else:
            print(f'❌ 路径不存在：{args.input}', file=sys.stderr)
            sys.exit(1)

    cache = get_cache_dir(args.slug)
    print(f'\n字幕文件已缓存至：{cache}')

    # 素材量检查
    result = check_material_sufficiency(cache)
    print(result['message'])

    print('下一步：将缓存目录提供给 Claude 进行四层分析')


if __name__ == '__main__':
    main()
