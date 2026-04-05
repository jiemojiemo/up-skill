"""
tests/test_install.py — install_helper.py 的单元测试

验证：
1. render_template 正确替换 {{UPS_DIR}} 占位符
2. get_agent_config 返回各 agent 的路径配置
3. install_to_agent 复制文件并替换占位符
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))
from install_helper import render_template, get_agent_config, install_to_agent


# ── render_template ──────────────────────────────────────────────────────────

def test_RenderTemplate_ReplacesUpsDir():
    template = "写入 {{UPS_DIR}}/{slug}/persona.md"
    result = render_template(template, ups_dir="/home/user/.claude/skills")
    assert result == "写入 /home/user/.claude/skills/{slug}/persona.md"


def test_RenderTemplate_ReplacesMultipleOccurrences():
    template = "{{UPS_DIR}}/a\n{{UPS_DIR}}/b"
    result = render_template(template, ups_dir="/target")
    assert "{{UPS_DIR}}" not in result
    assert result.count("/target") == 2


def test_RenderTemplate_PreservesSkillDirPlaceholder():
    template = "${SKILL_DIR}/prompts/intake.md and {{UPS_DIR}}/{slug}"
    result = render_template(template, ups_dir="/skills")
    assert "${SKILL_DIR}" in result
    assert "{{UPS_DIR}}" not in result


def test_RenderTemplate_NoPlaceholderReturnsUnchanged():
    template = "no placeholders here"
    result = render_template(template, ups_dir="/whatever")
    assert result == "no placeholders here"


# ── get_agent_config ─────────────────────────────────────────────────────────

def test_GetAgentConfig_ClaudeReturnsCorrectPaths():
    config = get_agent_config("claude", home=Path("/home/user"))
    assert config["skills_dir"] == Path("/home/user/.claude/skills")
    assert config["skill_dest"] == Path("/home/user/.claude/skills/up-skill")


def test_GetAgentConfig_CodexReturnsCorrectPaths():
    config = get_agent_config("codex", home=Path("/home/user"))
    assert config["skills_dir"] == Path("/home/user/.codex/skills")
    assert config["skill_dest"] == Path("/home/user/.codex/skills/up-skill")


def test_GetAgentConfig_UnknownAgentRaisesError():
    with pytest.raises(ValueError, match="不支持"):
        get_agent_config("unknown_agent", home=Path("/home/user"))


# ── install_to_agent ─────────────────────────────────────────────────────────

def _setup_source(tmp_path):
    """创建模拟的源项目目录"""
    source = tmp_path / "source"
    source.mkdir()
    # 主 SKILL.md
    (source / "SKILL.md").write_text(
        "---\nname: create-up\n---\n写入 {{UPS_DIR}}/{slug}/\n",
        encoding="utf-8",
    )
    # tools/
    (source / "tools").mkdir()
    (source / "tools" / "skill_writer.py").write_text("# writer", encoding="utf-8")
    # prompts/
    (source / "prompts").mkdir()
    (source / "prompts" / "intake.md").write_text("# intake", encoding="utf-8")
    # 管理 skill
    for name in ("list-ups", "update-up", "delete-up"):
        d = source / "skills" / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\n---\n{{{{UPS_DIR}}}}/up-skill\n",
            encoding="utf-8",
        )
    return source


def test_InstallToAgent_CopiesSkillMdToTarget(tmp_path):
    source = _setup_source(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    install_to_agent("claude", source_dir=source, home=home)
    assert (home / ".claude" / "skills" / "up-skill" / "SKILL.md").exists()


def test_InstallToAgent_ReplacesUpsDirInSkillMd(tmp_path):
    source = _setup_source(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    install_to_agent("claude", source_dir=source, home=home)
    content = (home / ".claude" / "skills" / "up-skill" / "SKILL.md").read_text()
    assert "{{UPS_DIR}}" not in content
    skills_dir = str(home / ".claude" / "skills")
    assert skills_dir in content


def test_InstallToAgent_CopiesManagementSkills(tmp_path):
    source = _setup_source(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    install_to_agent("claude", source_dir=source, home=home)
    for name in ("list-ups", "update-up", "delete-up"):
        skill_md = home / ".claude" / "skills" / name / "SKILL.md"
        assert skill_md.exists(), f"{name}/SKILL.md should be installed"


def test_InstallToAgent_ReplacesUpsDirInManagementSkills(tmp_path):
    source = _setup_source(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    install_to_agent("claude", source_dir=source, home=home)
    content = (home / ".claude" / "skills" / "list-ups" / "SKILL.md").read_text()
    assert "{{UPS_DIR}}" not in content


def test_InstallToAgent_CopiesTool(tmp_path):
    source = _setup_source(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    install_to_agent("claude", source_dir=source, home=home)
    assert (home / ".claude" / "skills" / "up-skill" / "tools" / "skill_writer.py").exists()


def test_InstallToAgent_CopiesPrompts(tmp_path):
    source = _setup_source(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    install_to_agent("claude", source_dir=source, home=home)
    assert (home / ".claude" / "skills" / "up-skill" / "prompts" / "intake.md").exists()
