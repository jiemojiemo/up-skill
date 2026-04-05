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
├── install.sh               # 多 Agent 安装脚本
├── pyproject.toml           # 项目配置与依赖
├── prompts/                 # 11 个 LLM prompt 模板（analyzer + builder 配对）
├── skills/                  # 独立管理 Skill（install 时复制到 agent skills 目录）
│   ├── list-ups/SKILL.md
│   ├── update-up/SKILL.md
│   └── delete-up/SKILL.md
├── tools/                   # Python 工具
│   ├── collector.py         # 素材采集（字幕/本地视频/链接/主页）
│   ├── subtitle_parser.py   # 字幕解析 → 纯文本
│   ├── asr_engine.py        # Whisper ASR 引擎
│   ├── skill_writer.py      # Skill 文件管理
│   ├── install_helper.py    # 安装辅助（占位符替换 + 文件复制）
│   ├── cache_manager.py     # 字幕缓存管理
│   ├── incremental.py       # 增量更新
│   ├── material_check.py    # 素材完整性检查
│   └── text_cleaner.py      # 文本清洗
├── tests/                   # 单测
├── docs/                    # 文档和待办
└── ups/                     # 本地开发用（gitignored）
```

## 约定

- slug 命名：中文名 → pypinyin 转拼音，下划线连接
- 版本管理：meta.json 中 semver patch 递增，旧版归档到 `{slug}/.versions/`
- 转录缓存：`~/.up-skill/cache/{slug}/transcripts/`
- 安装方式：`./install.sh install_claude` 或 `install_codex`，自动复制到 agent skills 目录
- SKILL.md 中用 `{{UPS_DIR}}` 占位符，install 时替换为实际路径
- ups/ 仅用于本地开发调试（gitignored）
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
4. 输出写入 agent skills 目录下的 `{slug}/`（4 个 .md + SKILL.md + meta.json）

## 常用命令

```bash
uv run pytest tests/                # 跑测试
uv run python3 tools/collector.py   # 素材采集
uv run python3 tools/skill_writer.py  # 写入 Skill
```
