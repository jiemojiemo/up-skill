# up-skill 安装说明

## 前置依赖

需要先安装 [uv](https://docs.astral.sh/uv/)：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 安装

```bash
git clone https://github.com/jiemojiemo/up-skill
cd up-skill
uv sync
```

然后根据你使用的 AI Agent 选择安装命令：

```bash
# Claude Code
./install.sh install_claude

# Codex CLI
./install.sh install_codex

# 同时安装到多个 Agent
./install.sh install_claude && ./install.sh install_codex
```

安装后会注册以下 Skill：
- `/create-up` — 创建 UP 主数字分身
- `/list-ups` — 列出所有已生成的 UP 主
- `/update-up` — 更新已有 UP 主（追加素材/纠错）
- `/delete-up` — 删除 UP 主 Skill

## 卸载

```bash
./install.sh uninstall_claude
./install.sh uninstall_codex
```

## 外部工具

### yt-dlp（必需）

用于从 B 站下载字幕和视频。已包含在 `uv sync` 中，也可单独安装：

```bash
brew install yt-dlp   # macOS
```

B 站需要登录态才能访问，工具会自动从 Chrome 读取 cookies：
```bash
# 确保你已在 Chrome 中登录 B 站
yt-dlp --cookies-from-browser chrome <url>
```

### whisper（可选，无官方字幕时使用）

已包含在 `uv sync` 中（openai-whisper、mlx-whisper、faster-whisper）。首次运行会自动下载模型（tiny 模型约 75MB）。

## 使用

在 Agent 中说 `/create-up` 启动，或直接说：

```
帮我蒸馏一个 UP 主，主页是 https://space.bilibili.com/946974
```

生成的 UP 主 Skill 会自动注册到 Agent 的 skills 目录，全局可用。
