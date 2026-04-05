"""
install_helper.py — 多 agent 安装辅助工具

将 up-skill 项目安装到不同 AI agent 的 skills 目录，
替换 {{UPS_DIR}} 占位符为实际路径。
"""

import argparse
import shutil
from pathlib import Path

AGENT_CONFIGS = {
    "claude": {"skills_subdir": ".claude/skills"},
    "codex": {"skills_subdir": ".codex/skills"},
}

# 安装时需要复制的目录/文件（相对于源项目根目录）
COPY_ITEMS = ["SKILL.md", "tools", "prompts", "pyproject.toml", "uv.lock", ".python-version"]

# 管理 skill 目录名
MANAGEMENT_SKILLS = ["list-ups", "update-up", "delete-up"]


def render_template(content: str, ups_dir: str) -> str:
    """替换 {{UPS_DIR}} 占位符"""
    return content.replace("{{UPS_DIR}}", ups_dir)


def get_agent_config(agent: str, home: Path = Path.home()) -> dict:
    """返回指定 agent 的路径配置"""
    if agent not in AGENT_CONFIGS:
        raise ValueError(f"不支持的 agent: {agent}，可选: {', '.join(AGENT_CONFIGS)}")
    cfg = AGENT_CONFIGS[agent]
    skills_dir = home / cfg["skills_subdir"]
    return {
        "skills_dir": skills_dir,
        "skill_dest": skills_dir / "up-skill",
    }


def install_to_agent(agent: str, source_dir: Path, home: Path = Path.home()) -> None:
    """安装 up-skill 到指定 agent 的 skills 目录"""
    config = get_agent_config(agent, home=home)
    skills_dir = config["skills_dir"]
    skill_dest = config["skill_dest"]
    ups_dir = str(skills_dir)

    # 复制主项目
    skill_dest.mkdir(parents=True, exist_ok=True)
    for item in COPY_ITEMS:
        src = source_dir / item
        dst = skill_dest / item
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        elif src.is_file():
            shutil.copy2(src, dst)

    # 替换主 SKILL.md 中的占位符
    skill_md = skill_dest / "SKILL.md"
    if skill_md.exists():
        content = skill_md.read_text(encoding="utf-8")
        content = render_template(content, ups_dir=ups_dir)
        skill_md.write_text(content, encoding="utf-8")

    # 复制管理 skill 并替换占位符
    for name in MANAGEMENT_SKILLS:
        src_dir = source_dir / "skills" / name
        if not src_dir.exists():
            continue
        dst_dir = skills_dir / name
        dst_dir.mkdir(parents=True, exist_ok=True)
        for f in src_dir.iterdir():
            shutil.copy2(f, dst_dir / f.name)
        mgmt_skill_md = dst_dir / "SKILL.md"
        if mgmt_skill_md.exists():
            content = mgmt_skill_md.read_text(encoding="utf-8")
            content = render_template(content, ups_dir=ups_dir)
            mgmt_skill_md.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="安装 up-skill 到 AI agent")
    parser.add_argument("--agent", required=True, choices=list(AGENT_CONFIGS.keys()))
    parser.add_argument("--source-dir", default=".", help="up-skill 项目根目录")
    args = parser.parse_args()
    install_to_agent(args.agent, source_dir=Path(args.source_dir))
    print(f"✅ 已安装到 {args.agent}")


if __name__ == "__main__":
    main()
