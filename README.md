<div align="center">

# UP 主.skill

> *"三分钟带你看完这个 README，一键三连的我都蒸馏了"*

[![Python 3.13+](https://img.shields.io/badge/Python-3.13%2B-blue.svg)](https://python.org)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-blueviolet)](https://github.com/anthropics/agent-skills)

<br>

你追的 UP 主停更了，再也等不到下一期？<br>
你喜欢的博主风格独特，想让 AI 也能这样说话？<br>
你做内容想参考某个 UP 主的选题思路，却只能一条条翻视频？<br>
你写脚本想模仿他的节奏，但怎么写都不像？<br>

**给一个主页链接，自动蒸馏出他的数字分身。**

<br>

自动采集视频字幕，分析语气、选题、节奏、边界<br>
生成一个**能像他一样聊天、做选题、写脚本的 AI Skill**<br>
用他的口头禅回答问题，用他的套路起标题，知道他什么话题绝对不碰

[数据来源](#支持的数据来源) · [安装](#安装) · [使用](#使用) · [效果示例](#效果示例) · [详细安装说明](INSTALL.md)

</div>

---

## 支持的数据来源

| 来源 | 方式 | 推荐度 | 备注 |
|------|------|:------:|------|
| B 站主页链接 | 全自动采集 | ⭐⭐⭐ | 输入 `space.bilibili.com` 链接，自动抓字幕 |
| 视频链接 | 自动采集 | ⭐⭐⭐ | 一个或多个 `bilibili.com/video/` 链接 |
| .srt / .vtt 字幕文件 | 手动上传 | ⭐⭐ | 直接解析，最稳定 |
| 本地视频文件夹 | Whisper ASR | ⭐⭐ | 无字幕时自动转录 |
| 直接粘贴逐字稿 | 手动输入 | ⭐ | 有多少贴多少 |
| 手动描述风格 | 手动输入 | ⭐ | 仅凭描述也能生成，但精度有限 |

> 推荐用主页链接自动采集 5-20 条视频字幕，素材越多分身越准。

---

## 前置条件

1. 安装 [uv](https://docs.astral.sh/uv/)（Python 包管理，`curl -LsSf https://astral.sh/uv/install.sh | sh`）
2. 安装一个支持 [Agent Skills](https://github.com/anthropics/agent-skills) 的 AI Agent（如 [Claude Code](https://docs.anthropic.com/en/docs/claude-code)、[Codex CLI](https://github.com/openai/codex) 等）
3. B 站自动采集需要 Chrome 或 Firefox 已登录 B 站（yt-dlp 读取 cookies，已包含在依赖中）

## 安装

懒得看下面的步骤？直接把这个链接丢给你的 Agent，让它帮你装：

```
帮我安装这个 skill：https://github.com/jiemojiemo/up-skill
```

<details>
<summary>手动安装</summary>

```bash
git clone https://github.com/jiemojiemo/up-skill
cd up-skill
uv sync
```

根据你使用的 Agent 选择安装命令：

```bash
# Claude Code
./install.sh install_claude

# Codex CLI
./install.sh install_codex

# 同时装多个
./install.sh install_claude && ./install.sh install_codex
```

> 已安装过？`git pull && ./install.sh install_claude` 更新到最新版。

</details>

### 验证安装

启动你的 Agent，输入 `/create-up`。如果开始问你 UP 主的名字，说明安装成功。

---

## 使用

在 Agent 对话中输入（不是在终端里）：

```
/create-up
```

按提示输入 UP 主名称、基本信息（如 `B站 科技区 百万粉 男`）、风格标签，然后提供素材来源。所有字段均可跳过，仅凭描述也能生成。

也可以直接给主页链接，跳过手动输入：

```
/create-up https://space.bilibili.com/946974
```

完成后用 `/{slug}` 调用该 UP 主的数字分身（见下方用法示例）。

### 管理命令

| 命令 | 说明 |
|------|------|
| `/list-ups` | 列出所有已生成的 UP 主 Skill |
| `/update-up {slug}` | 追加素材，进化分身 |
| `/delete-up {slug}` | 删除 |

### 怎么用

生成完成后，用 `/{slug}` 调用该 UP 主的数字分身，然后直接用自然语言告诉它你想做什么：

```
/bidao 苹果刚发了 Vision Pro 2，帮我做个选题分析
```

```
/bidao 帮我写一期关于「为什么手机越来越重」的口播脚本
```

```
/bidao 帮我看看这个标题行不行：《震惊！这款相机吊打所有对手》
```

不需要记子命令，直接说需求就行。分身会根据四层人设自动判断该怎么回应。

---

## 效果示例

> 输入：`影视飓风 B站 科技区 百万粉 男 理性客观 数据驱动 反消费主义`

**做选题**

```
用户          ❯ /ysjf 苹果刚发了 Vision Pro 2，要不要做一期？

影视飓风.skill ❯ 做，但不做开箱评测，那是别人的活。
               我们的角度：它的显示技术到底比一代强在哪？
               用数据说话，拆解面板参数，对比实际观感。
               标题：《Vision Pro 2 的屏幕，真的值这个价吗？》
```

**检查风格**

```
用户          ❯ /ysjf 帮我看看这个标题：《震惊！这款相机吊打所有对手》

影视飓风.skill ❯ 3/10。两个问题：
               1.「震惊」是标题党，他从来不用
               2.「吊打所有对手」太绝对，他会说「在这个价位段很难找到对手」
               建议改：《这个价位的相机，还有对手吗？》
```

---

## 四层分身结构

每个 UP 主 Skill 由四层组成，共同驱动输出：

| 层 | 内容 |
|---|------|
| **Persona** | 语气、口头禅、互动风格、人设标签 |
| **Content Brain** | 选题偏好、标志性观点、知识边界 |
| **Production Style** | 标题套路、开头 Hook、口播节奏、剪辑风格 |
| **Brand Guardrails** | 商业边界、话题红线、翻车风险 |

运行逻辑：`收到任务 → Persona 决定态度 → Content Brain 判断能不能做 → Production Style 执行 → Brand Guardrails 兜底`

### 进化机制

- **追加素材** → 自动分析增量 → merge 进对应层，不覆盖已有结论
- **对话纠正** → 说「他不会这样说，他应该是 xxx」→ 写入 Correction 层，立即生效
- **版本管理** → 每次更新自动存档到 `.versions/`，支持回滚

---

## 项目结构

```
up-skill/
├── SKILL.md              # Skill 入口（name: create-up）
├── install.sh            # 多 Agent 安装脚本
├── pyproject.toml        # 项目配置与依赖
├── skills/               # 独立管理 Skill
│   ├── list-ups/         #   /list-ups
│   ├── update-up/        #   /update-up
│   └── delete-up/        #   /delete-up
├── prompts/              # Prompt 模板
│   ├── intake.md         #   信息录入
│   ├── persona_analyzer.md / persona_builder.md
│   ├── content_brain_analyzer.md / content_brain_builder.md
│   ├── production_style_analyzer.md / production_style_builder.md
│   ├── brand_guardrails_analyzer.md / brand_guardrails_builder.md
│   ├── merger.md         #   四层合并
│   └── correction_handler.md
├── tools/                # Python 工具
│   ├── collector.py      #   数据采集（主页/链接/本地）
│   ├── subtitle_parser.py #  字幕解析
│   ├── asr_engine.py     #   Whisper ASR
│   ├── skill_writer.py   #   Skill 文件管理
│   ├── install_helper.py #   安装辅助
│   ├── cache_manager.py  #   缓存管理
│   ├── incremental.py    #   增量更新
│   ├── material_check.py #   素材完整性检查
│   └── text_cleaner.py   #   文本清洗
├── tests/                # 单元测试
└── ups/                  # 本地开发用（gitignored）
```

---

## 注意事项

- **素材质量决定分身质量**：自动采集 10+ 条视频字幕 > 手动描述
- 建议优先采集：**观点输出型视频** > 教程类 > 纯 vlog
- B 站自动采集需要 Chrome 或 Firefox 已登录 B 站（yt-dlp 读取 cookies，已包含在依赖中）
- 字幕缓存在 `~/.up-skill/cache/{slug}/transcripts/`，下次蒸馏同一个 UP 主直接复用

---

## 灵感来源

基于 [colleague-skill](https://github.com/titanwings/colleague-skill) 的设计模式，针对 UP 主内容创作场景重新设计四层结构。

---

<div align="center">

MIT License © [jiemojiemo](https://github.com/jiemojiemo)

</div>
