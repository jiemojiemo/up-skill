# up-skill

把 B 站 UP 主蒸馏成可调用的 AI Skill。

给一个主页链接，自动采集视频字幕，生成四层数字分身：

- **Persona** — 语气、口头禅、互动风格
- **Content Brain** — 选题偏好、标志性观点、知识边界
- **Production Style** — 标题套路、开头 Hook、口播节奏
- **Brand Guardrails** — 商业边界、话题红线、翻车风险

生成后可以用四种方式调用：

```
/{slug}              → 像他聊天
/{slug}-brainstorm   → 像他做选题会
/{slug}-script       → 像他写口播脚本
/{slug}-check        → 检查内容是否符合他的风格边界
```

---

## 快速开始

```bash
git clone https://github.com/jiemojiemo/up-skill ~/.claude/skills/up-skill
cd ~/.claude/skills/up-skill
uv sync
```

然后在 Claude Code 中说 `/create-up`，告诉 Claude UP 主的主页链接，剩下的它来做。

---

## 数据管道

```
优先级 1：用户提供 .srt/.vtt/.txt 字幕文件   → 直接解析
优先级 2：用户提供本地视频文件夹              → whisper ASR
优先级 3：用户提供视频链接                   → yt-dlp 抓字幕 / ASR
优先级 4：用户提供 UP 主主页 URL             → 自动列出视频 → 批量处理
```

字幕缓存在本地 `~/.up-skill/cache/{slug}/transcripts/`，下次蒸馏同一个 UP 主直接复用。

---

## 目录结构

```
up-skill/
├── .claude-plugin/
│   ├── plugin.json             # 插件元数据
│   └── marketplace.json        # marketplace 发布配置
├── skills/
│   └── up-skill/
│       └── SKILL.md            # Skill 入口
├── prompts/                    # 分析和生成的 Prompt 模板
│   ├── intake.md
│   ├── persona_analyzer.md
│   ├── content_brain_analyzer.md
│   ├── production_style_analyzer.md
│   ├── brand_guardrails_analyzer.md
│   ├── persona_builder.md
│   ├── content_brain_builder.md
│   ├── production_style_builder.md
│   ├── brand_guardrails_builder.md
│   ├── merger.md
│   └── correction_handler.md
├── tools/                      # Python 工具脚本
│   ├── collector.py            # 数据采集主入口
│   ├── subtitle_parser.py      # 字幕解析
│   ├── skill_writer.py         # Skill 文件管理
│   ├── asr_engine.py           # Whisper ASR 引擎
│   ├── cache_manager.py        # 字幕缓存管理
│   ├── incremental.py          # 增量更新
│   ├── material_check.py       # 素材完整性检查
│   └── text_cleaner.py         # 文本清洗
├── tests/                      # 单元测试
└── ups/                        # 生成的 UP 主 Skill（本地，不提交）
    └── {slug}/
        ├── SKILL.md
        ├── persona.md
        ├── content_brain.md
        ├── production_style.md
        ├── brand_guardrails.md
        └── meta.json
```

---

## 依赖

- `yt-dlp` — 视频/字幕下载
- `openai-whisper` — 语音转文字（无官方字幕时使用）
- `pypinyin` — 中文名转拼音 slug

详见 [INSTALL.md](INSTALL.md)。

---

## 灵感来源

基于 [colleague-skill](https://github.com/titanwings/colleague-skill) 的设计模式，针对 UP 主内容创作场景重新设计四层结构。
