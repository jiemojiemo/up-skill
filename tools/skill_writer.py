#!/usr/bin/env python3
"""
skill_writer.py — 创建和管理 UP 主 Skill 文件

用法：
  uv run python3 skill_writer.py --action create --slug <slug> --name <name> [options]
  uv run python3 skill_writer.py --action list --base-dir ./ups
  uv run python3 skill_writer.py --action version --slug <slug> --base-dir ./ups
"""

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from pypinyin import lazy_pinyin


def slugify(name: str) -> str:
    """中文名 → 拼音下划线连接，英文名 → 小写下划线连接"""
    name = name.strip()
    # 如果包含中文字符，用 pypinyin 转换
    if re.search(r'[\u4e00-\u9fff]', name):
        parts = lazy_pinyin(name)
        name = '_'.join(parts)
    else:
        name = name.lower()
        name = re.sub(r'[\s\-]+', '_', name)
    name = re.sub(r'[^\w]', '', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    return name


def get_base_dir(base_dir: str) -> Path:
    return Path(base_dir)


def create_skill(slug: str, name: str, base_dir: Path, meta: dict) -> Path:
    """创建 UP 主 Skill 目录结构"""
    skill_dir = base_dir / slug
    skill_dir.mkdir(parents=True, exist_ok=True)

    # 写入空白四层文件（如果不存在）
    for layer in ('persona.md', 'content_brain.md', 'production_style.md', 'brand_guardrails.md'):
        layer_path = skill_dir / layer
        if not layer_path.exists():
            layer_name = layer.replace('.md', '').replace('_', ' ').title()
            layer_path.write_text(f'# {name} — {layer_name}\n\n（待生成）\n', encoding='utf-8')

    # 写入 meta.json
    now = datetime.now(timezone.utc).isoformat()
    meta_data = {
        'name': name,
        'slug': slug,
        'platform': meta.get('platform', ''),
        'domain': meta.get('domain', ''),
        'followers': meta.get('followers', ''),
        'version': '1.0.0',
        'created_at': now,
        'updated_at': now,
        'source_materials': [],
        'layers': ['persona', 'content_brain', 'production_style', 'brand_guardrails'],
    }
    (skill_dir / 'meta.json').write_text(
        json.dumps(meta_data, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    print(f'✅ 已创建 {name} ({slug}) 在 {skill_dir}')
    return skill_dir


def bump_version(skill_dir: Path) -> str:
    """递增版本号，更新 meta.json 的 updated_at"""
    meta_path = skill_dir / 'meta.json'
    if not meta_path.exists():
        return '1.0.0'
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    parts = meta.get('version', '1.0.0').split('.')
    parts[-1] = str(int(parts[-1]) + 1)
    new_version = '.'.join(parts)
    meta['version'] = new_version
    meta['updated_at'] = datetime.now(timezone.utc).isoformat()
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    return new_version


def archive_version(skill_dir: Path) -> Path:
    """将当前版本归档到 .versions/ 目录"""
    meta_path = skill_dir / 'meta.json'
    if not meta_path.exists():
        return skill_dir
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    version = meta.get('version', '1.0.0')
    archive_dir = skill_dir / '.versions' / version
    archive_dir.mkdir(parents=True, exist_ok=True)
    for f in ('persona.md', 'content_brain.md', 'production_style.md',
              'brand_guardrails.md', 'SKILL.md', 'meta.json'):
        src = skill_dir / f
        if src.exists():
            shutil.copy2(src, archive_dir / f)
    return archive_dir


def list_skills(base_dir: Path) -> None:
    """列出所有已生成的 UP 主"""
    if not base_dir.exists():
        print('（暂无 UP 主）')
        return
    skills = []
    for d in sorted(base_dir.iterdir()):
        if not d.is_dir():
            continue
        meta_path = d / 'meta.json'
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            skills.append(meta)
    if not skills:
        print('（暂无 UP 主）')
        return
    print(f'{"名字":<15} {"Slug":<25} {"平台":<8} {"版本":<8} {"更新时间"}')
    print('-' * 75)
    for m in skills:
        updated = m.get('updated_at', '')[:10]
        print(f'{m["name"]:<15} {m["slug"]:<25} {m.get("platform",""):<8} {m.get("version",""):<8} {updated}')


def main():
    parser = argparse.ArgumentParser(description='UP 主 Skill 文件管理')
    parser.add_argument('--action', choices=['create', 'list', 'version', 'archive'],
                        required=True)
    parser.add_argument('--slug', help='UP 主 slug')
    parser.add_argument('--name', help='UP 主名字')
    parser.add_argument('--base-dir', default='./ups', help='Skill 根目录')
    parser.add_argument('--platform', default='')
    parser.add_argument('--domain', default='')
    parser.add_argument('--followers', default='')
    args = parser.parse_args()

    base_dir = get_base_dir(args.base_dir)

    if args.action == 'list':
        list_skills(base_dir)

    elif args.action == 'create':
        if not args.slug or not args.name:
            print('错误：create 需要 --slug 和 --name', file=sys.stderr)
            sys.exit(1)
        slug = args.slug or slugify(args.name)
        create_skill(slug, args.name, base_dir, {
            'platform': args.platform,
            'domain': args.domain,
            'followers': args.followers,
        })

    elif args.action == 'version':
        if not args.slug:
            print('错误：version 需要 --slug', file=sys.stderr)
            sys.exit(1)
        skill_dir = base_dir / args.slug
        new_ver = bump_version(skill_dir)
        print(f'版本已更新至 {new_ver}')

    elif args.action == 'archive':
        if not args.slug:
            print('错误：archive 需要 --slug', file=sys.stderr)
            sys.exit(1)
        skill_dir = base_dir / args.slug
        archive_dir = archive_version(skill_dir)
        print(f'已归档至 {archive_dir}')


if __name__ == '__main__':
    main()
