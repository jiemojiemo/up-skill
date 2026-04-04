# up-skill

把 B 站 UP 主蒸馏成可调用的 AI Skill。

## 技术栈

- Python 3.13，包管理用 uv
- 测试：pytest，运行 `uv run pytest tests/`
- ASR 依赖：mlx-whisper（Apple Silicon）、openai-whisper（fallback）
- 视频下载：yt-dlp
- 拼音转换：pypinyin

## 项目结构

```
up-skill/
├── SKILL.md                 # Skill 入口（name: create-up）
├── requirements.txt         # 运行时依赖
├── prompts/                 # 11 个 LLM prompt 模板（analyzer + builder 配对）
├── tools/                   # Python 工具
│   ├── collector.py         # 素材采集（字幕/本地视频/链接/主页）
│   ├── subtitle_parser.py   # 字幕解析 → 纯文本
│   └── skill_writer.py      # 写入 ups/{slug}/ 目录结构
├── tests/                   # 单测
├── docs/                    # 文档和待办
└── ups/                     # 生成的 Skill（gitignored）
```

## 约定

- slug 命名：中文名 → pypinyin 转拼音，下划线连接
- 版本管理：meta.json 中 semver patch 递增，旧版归档到 `ups/{slug}/.versions/`
- 转录缓存：`~/.up-skill/cache/{slug}/transcripts/`
- ups/ 已 gitignore，生成的 Skill 不提交到本 repo
- 响应语言跟随用户（中英文自适应）

## 四层架构

每个 UP 主 Skill 由四层组成：

| 层 | 文件 | 作用 |
|---|---|---|
| Persona | persona.md | 语气、口头禅、互动风格 |
| Content Brain | content_brain.md | 选题偏好、标志性观点、知识边界 |
| Production Style | production_style.md | 标题套路、开头 Hook、口播节奏 |
| Brand Guardrails | brand_guardrails.md | 商业边界、话题红线、翻车风险 |

## 生成流程

1. `/create-up` 触发 intake（3 个问题：名称、基本信息、人设描述）
2. 素材采集 → ASR 转录 → 纯文本
3. 四层分析（analyzer prompt → builder prompt）
4. 输出写入 `ups/{slug}/`（4 个 .md + SKILL.md + meta.json）

## 常用命令

```bash
uv run pytest tests/              # 跑测试
uv run python tools/collector.py  # 素材采集
uv run python tools/skill_writer.py  # 写入 Skill
```
