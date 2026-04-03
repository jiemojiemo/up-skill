# up-skill TODO

> 讨论日期：2025-07-26

---

## 1. ASR 多后端引擎

当前 whisper CPU 太慢，cohere-transcribe 部署重。需要根据硬件自动选择最优 ASR 引擎。

| 硬件 | 引擎 | 预估速度 |
|---|---|---|
| Apple Silicon (M系列) | mlx-whisper | ~5-10x 实时 |
| NVIDIA GPU | faster-whisper (CUDA) | ~10-20x 实时 |
| 其他 CPU | faster-whisper (CPU mode) | ~2-3x 实时 |

- [ ] 实现引擎自动检测（Apple Silicon / NVIDIA / CPU）
- [ ] 集成 mlx-whisper
- [ ] 集成 faster-whisper
- [ ] 支持用户手动指定引擎覆盖自动检测

---

## 2. up-skill-gallery 独立仓库

生成好的 Skill 放独立 repo，主 repo 保持框架代码干净。

- [ ] 创建 up-skill-gallery 仓库
- [ ] ups/ 继续 gitignore
- [ ] gallery 按 slug 目录组织，附 README 说明

---

## 3. 素材源扩展

当前只支持视频 ASR，需要支持更多文本来源。

| 来源 | 处理方式 |
|---|---|
| 视频（现有） | yt-dlp → ASR → 文本 |
| 本地文档 | .md / .txt / .pdf 直接读取 |
| 文章链接 | 抓取网页正文（readability 提取） |
| B站专栏 / 公众号 | 按平台适配抓取 |

- [ ] 支持本地 .md / .txt / .pdf 解析
- [ ] 支持文章链接抓取（readability 正文提取）
- [ ] 统一输出纯文本，复用现有 analyzer prompts

---

## 4. 子命令精简

删除没有真实素材支撑的命令，修正描述不一致问题。

调整后保留四个：

```
/{slug}              → 像他聊天
/{slug}-brainstorm   → 像他做选题会
/{slug}-script       → 像他写口播脚本
/{slug}-check        → 检查内容是否符合他的风格边界
```

- [ ] 删除 `/{slug}-comment` 和 `/{slug}-live`
- [ ] `-brand` 改名为 `-check`，描述改为"检查内容是否符合他的风格边界"
- [ ] 同步更新 SKILL.md 和 README.md

---

## 5. 音频下载优化

只下载最低质量音频流，直接转 16kHz 单声道，最小化存储压力。

```bash
yt-dlp -f "worstaudio" -x --audio-format wav \
  --postprocessor-args "ffmpeg:-ar 16000 -ac 1" <url>
```

- [ ] collector 中使用 worstaudio + 16kHz 单声道策略
- [ ] 不下载视频画面

---

## 6. 生成质量校验

四层文件生成后自动 self-check，避免 ASR 垃圾文本污染 Skill 质量。

- [ ] 生成后用 Skill 回答预设问题，对比原始素材检查偏差
- [ ] ASR 输出预处理：检测并清理尾部重复垃圾文本

---

## 7. 素材量下限提醒

素材太少会导致 Skill 过拟合到个别视频风格。

- [ ] 素材不足时给出提示："建议至少 5 个视频 / 30 分钟素材以获得较准确的分身"

---

## 8. 增量更新

当前加新素材需要重新生成全部四层，效率低。

- [ ] 新素材只产出增量分析
- [ ] 增量结果与已有四层 merge，而非从头生成

---

## 9. 缓存管理

下载的音频和转录文本会持续增长。

- [ ] 添加 `up-skill clean` 命令清理缓存
- [ ] 可选：转录完成后自动删除音频，只保留文本

---

## 10. 项目结构重构为 Plugin

当前 Skill 内容和工具代码混在根目录，不符合 Claude Code plugin 规范。参考 [obra/superpowers](https://github.com/obra/superpowers) 的结构，重构为标准 plugin 格式，支持 `claude install` 安装。

目标结构：

```
up-skill/
├── .claude-plugin/
│   ├── plugin.json             # 插件元数据（name, version, description, author）
│   └── marketplace.json        # marketplace 发布配置（可选）
├── skills/
│   └── up-skill/
│       └── SKILL.md            # Skill 入口（从根目录移入）
├── prompts/                    # 分析/构建模板
├── tools/                      # Python 工具代码
├── scripts/                    # 辅助脚本
├── tests/                      # 测试
├── docs/
│   └── TODO.md
└── README.md
```

核心原则（参考 superpowers）：
- skills/ 目录只放 SKILL.md，纯指令，不混代码
- 工具代码放 tools/、scripts/ 等独立目录
- plugin.json 定义元数据，支持 marketplace 分发

- [ ] 创建 `.claude-plugin/plugin.json`
- [ ] 创建 `.claude-plugin/marketplace.json`（可选）
- [ ] 将根目录 `SKILL.md` 移至 `skills/up-skill/SKILL.md`
- [ ] 验证 `claude --plugin-dir` 方式可正常加载
- [ ] 更新 README 说明安装方式（plugin install / plugin-dir / 手动）
