# up-skill 安装说明

## 安装到 Claude Code

```bash
# 方式 1：plugin install（推荐）
claude plugin install up-skill

# 方式 2：plugin-dir 本地加载
git clone https://github.com/yourname/up-skill
claude --plugin-dir ./up-skill

# 方式 3：手动安装
git clone https://github.com/yourname/up-skill ~/.claude/plugins/up-skill
```

## 安装依赖

本项目用 [uv](https://docs.astral.sh/uv/) 管理依赖。

```bash
cd <up-skill 目录>

# 安装 uv（如果还没有）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装所有依赖
uv sync
```

## 外部工具

### yt-dlp（必需）

用于从 B 站下载字幕和视频。

```bash
brew install yt-dlp   # macOS
# 或
pip install yt-dlp
```

B 站需要登录态才能访问，工具会自动从 Chrome 读取 cookies：
```bash
# 确保你已在 Chrome 中登录 B 站
yt-dlp --cookies-from-browser chrome <url>
```

### whisper（可选，无官方字幕时使用）

```bash
uv add openai-whisper
# 首次运行会自动下载模型（tiny 模型约 75MB）
```

## 快速验证

```bash
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
