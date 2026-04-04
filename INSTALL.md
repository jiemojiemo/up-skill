# up-skill 安装说明

## 安装到 Claude Code

```bash
# 安装到当前项目
mkdir -p .claude/skills
git clone https://github.com/jiemojiemo/up-skill .claude/skills/up-skill

# 或安装到全局
git clone https://github.com/jiemojiemo/up-skill ~/.claude/skills/up-skill
```

## 安装依赖

需要先安装 [uv](https://docs.astral.sh/uv/)：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

然后安装项目依赖：

```bash
cd ~/.claude/skills/up-skill   # 或你的 skill 安装路径
uv sync
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

## 快速验证

```bash
cd .claude/skills/up-skill

# 列出已有 UP 主
uv run python3 tools/skill_writer.py --action list --base-dir ./ups

# 测试字幕解析
uv run python3 tools/subtitle_parser.py --help

# 测试采集器
uv run python3 tools/collector.py --help

# 跑单元测试
uv run pytest tests/
```

## 使用

在 Claude Code 中说 `/create-up` 启动，或直接说：

```
帮我蒸馏一个 UP 主，主页是 https://space.bilibili.com/946974
```

生成的 UP 主 Skill 写入 `./ups/{slug}/`，默认不提交到 git（已加入 .gitignore）。
