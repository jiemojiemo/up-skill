#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

usage() {
    echo "用法: $0 <command>"
    echo ""
    echo "命令:"
    echo "  install_claude    安装到 Claude Code (~/.claude/skills/)"
    echo "  install_codex     安装到 Codex CLI (~/.codex/skills/)"
    echo "  uninstall_claude  从 Claude Code 卸载"
    echo "  uninstall_codex   从 Codex CLI 卸载"
    echo ""
    echo "示例:"
    echo "  $0 install_claude"
    echo "  $0 install_claude && $0 install_codex  # 同时装两个"
}

install_claude() {
    echo "📦 安装到 Claude Code..."
    cd "$SCRIPT_DIR" && uv run python3 tools/install_helper.py --agent claude --source-dir "$SCRIPT_DIR"
    echo ""
    echo "安装完成。在 Claude Code 中输入 /create-up 开始使用。"
    echo "管理命令: /list-ups, /update-up, /delete-up"
}

install_codex() {
    echo "📦 安装到 Codex CLI..."
    cd "$SCRIPT_DIR" && uv run python3 tools/install_helper.py --agent codex --source-dir "$SCRIPT_DIR"
    echo ""
    echo "安装完成。在 Codex 中输入 /create-up 开始使用。"
    echo "管理命令: /list-ups, /update-up, /delete-up"
}

uninstall_claude() {
    echo "🗑  从 Claude Code 卸载..."
    rm -rf ~/.claude/skills/up-skill
    rm -rf ~/.claude/skills/list-ups
    rm -rf ~/.claude/skills/update-up
    rm -rf ~/.claude/skills/delete-up
    echo "已卸载。生成的 UP 主 Skill 未删除，如需清理请手动删除 ~/.claude/skills/ 下对应目录。"
}

uninstall_codex() {
    echo "🗑  从 Codex CLI 卸载..."
    rm -rf ~/.codex/skills/up-skill
    rm -rf ~/.codex/skills/list-ups
    rm -rf ~/.codex/skills/update-up
    rm -rf ~/.codex/skills/delete-up
    echo "已卸载。生成的 UP 主 Skill 未删除，如需清理请手动删除 ~/.codex/skills/ 下对应目录。"
}

case "${1:-}" in
    install_claude)  install_claude ;;
    install_codex)   install_codex ;;
    uninstall_claude) uninstall_claude ;;
    uninstall_codex)  uninstall_codex ;;
    -h|--help|"")    usage ;;
    *)
        echo "错误: 未知命令 '$1'"
        usage
        exit 1
        ;;
esac
