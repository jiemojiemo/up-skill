<div align="center">

# UP 主.skill

> *"三分钟带你看完这个 README，一键三连的我都蒸馏了"*

[![Python 3.13+](https://img.shields.io/badge/Python-3.13%2B-blue.svg)](https://python.org)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet)](https://claude.ai/code)

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

这是一个 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill，需要：

1. 安装 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI（终端输入 `claude` 启动）
2. 安装 [uv](https://docs.astral.sh/uv/)（Python 包管理，`curl -LsSf https://astral.sh/uv/install.sh | sh`）
3. B 站自动采集需要 Chrome 已登录 B 站（yt-dlp 读取 cookies）

## 安装

### Claude Code

> Claude Code 从 `~/.claude/skills/` 或项目内 `.claude/skills/` 查找 skill。

```bash
# 首次安装到全局（所有项目都能用，推荐）
git clone https://github.com/jiemojiemo/up-skill ~/.claude/skills/up-skill

# 已安装过？更新到最新版
cd ~/.claude/skills/up-skill && git pull

# 或安装到当前项目（在 git 仓库根目录执行）
mkdir -p .claude/skills
git clone https://github.com/jiemojiemo/up-skill .claude/skills/up-skill
```

### Codex

```bash
git clone https://github.com/jiemojiemo/up-skill ~/.codex/skills/up-skill
```

### 依赖（可选，自动采集需要）

```bash
cd ~/.claude/skills/up-skill && uv sync
```

> 自动采集依赖 `yt-dlp`，B 站需要 Chrome 已登录 B 站。无官方字幕时会用 Whisper ASR 转录（耗时约等于视频时长，10 个视频可能需要几十分钟）。详见 [INSTALL.md](INSTALL.md)。

### 验证安装

启动 Claude Code（终端输入 `claude`），然后输入 `/create-up`。如果 Claude 开始问你 UP 主的名字，说明 skill 已生效。

---

## 使用

在 Claude Code 对话中输入（不是在终端里）：

```
/create-up
```

按提示输入 UP 主名称、基本信息（如 `B站 科技区 百万粉 男`）、风格标签，然后提供素材来源。所有字段均可跳过，仅凭描述也能生成。

也可以直接给主页链接，跳过手动输入：

```
/create-up https://space.bilibili.com/946974
```

完成后用 `/{slug}` 调用该 UP 主 Skill。

### 管理命令

| 命令 | 说明 |
|------|------|
| `/list-ups` | 列出所有已生成的 UP 主 Skill |
| `/{slug}` | 像他一样聊天（陪伴/问答） |
| `/{slug}-brainstorm` | 像他一样做选题会 |
| `/{slug}-script` | 像他一样写口播脚本 |
| `/{slug}-check` | 检查内容是否符合他的风格边界 |
| `/update-up {slug}` | 追加素材，进化分身 |
| `/delete-up {slug}` | 删除 |

---

## 效果示例

> 输入：`影视飓风 B站 科技区 百万粉 男 理性客观 数据驱动 反消费主义`

**场景一：选题会**

```
用户          ❯ 苹果刚发了 Vision Pro 2，要不要做一期？

影视飓风.skill ❯ 做，但不做开箱评测，那是别人的活。
               我们的角度：它的显示技术到底比一代强在哪？
               用数据说话，拆解面板参数，对比实际观感。
               标题：《Vision Pro 2 的屏幕，真的值这个价吗？》
```

**场景二：风格检查**

```
用户          ❯ 帮我看看这个标题：《震惊！这款相机吊打所有对手》

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
├── pyproject.toml        # 项目配置与依赖
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
│   ├── cache_manager.py  #   缓存管理
│   ├── incremental.py    #   增量更新
│   ├── material_check.py #   素材完整性检查
│   └── text_cleaner.py   #   文本清洗
├── tests/                # 单元测试
└── ups/                  # 生成的 UP 主 Skill（gitignored）
```

---

## 注意事项

- **素材质量决定分身质量**：自动采集 10+ 条视频字幕 > 手动描述
- 建议优先采集：**观点输出型视频** > 教程类 > 纯 vlog
- B 站自动采集需要 Chrome 已登录 B 站（yt-dlp 读取 cookies）
- 字幕缓存在 `~/.up-skill/cache/{slug}/transcripts/`，下次蒸馏同一个 UP 主直接复用

---

## 灵感来源

基于 [colleague-skill](https://github.com/titanwings/colleague-skill) 的设计模式，针对 UP 主内容创作场景重新设计四层结构。

---

<div align="center">

MIT License © [jiemojiemo](https://github.com/jiemojiemo)

</div>
