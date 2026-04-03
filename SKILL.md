---
name: create-up
description: "Distill a Bilibili UP主 into an AI Skill. Parse subtitles/comments/live transcripts, generate Persona + Content Brain + Production Style + Brand Guardrails, with continuous evolution. | 把 UP 主蒸馏成 AI Skill，解析字幕/评论/直播转录，生成四层数字分身，支持持续进化。"
argument-hint: "[up-name-or-slug]"
version: "1.0.0"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash
---

> **语言**: 根据用户第一条消息的语言，全程使用同一语言回复。

# up-skill 创建器（Claude Code 版）

## 触发条件

当用户说以下任意内容时启动：
- `/create-up`
- "帮我创建一个 UP 主 skill"
- "我想蒸馏一个 UP 主"
- "给我做一个 XX 的 skill"

当用户对已有 UP 主 Skill 说以下内容时，进入进化模式：
- "我有新素材" / "追加"
- "这不对" / "他不会这样说" / "他应该是"
- `/update-up {slug}`

当用户说 `/list-ups` 时列出所有已生成的 UP 主。

---

## 工具使用规则

| 任务 | 使用工具 |
|------|---------|
| 读取字幕文件（.srt/.vtt/.txt） | `Read` 工具 |
| 读取截图/封面图 | `Read` 工具（原生支持图片） |
| 解析 B 站字幕 JSON | `Bash` → `python3 ${CLAUDE_SKILL_DIR}/tools/subtitle_parser.py` |
| 解析评论区导出 | `Bash` → `python3 ${CLAUDE_SKILL_DIR}/tools/comment_parser.py` |
| 写入/更新 Skill 文件 | `Write` / `Edit` 工具 |
| 列出已有 Skill | `Bash` → `python3 ${CLAUDE_SKILL_DIR}/tools/skill_writer.py --action list` |

**基础目录**：Skill 文件写入 `./ups/{slug}/`（相对于本项目目录）。

---

## 主流程：创建新 UP 主 Skill

### Step 1：基础信息录入（3 个问题）

参考 `${CLAUDE_SKILL_DIR}/prompts/intake.md` 的问题序列，只问 3 个问题：

1. **UP 主名/代号**（必填）
2. **基本信息**（一句话：平台、领域、粉丝量级、性别）
   - 示例：`B 站 科技区 百万粉 男`
3. **人设画像**（一句话：风格标签、个性、印象）
   - 示例：`毒舌 反消费主义 爱用数据说话 评论区互动很多`

除名字外均可跳过。收集完后汇总确认再进入下一步。

### Step 2：原材料导入

询问用户提供原材料，展示四种方式供选择：

```
原材料怎么提供？

  [A] 字幕文件（推荐）
      上传 .srt / .vtt / .txt 字幕，或直接粘贴逐字稿

  [B] 评论区导出
      上传评论区 CSV/JSON，或粘贴 UP 主的评论回复截图

  [C] 直播转录
      上传直播回放字幕或转录文本

  [D] 手动描述
      直接告诉我他的风格、口头禅、内容偏好
```

**最低要求**：至少提供 [A] 或 [D] 之一。原材料越多，四层分身越准确。

### Step 3：四层分析

收到原材料后，依次执行：

1. 参考 `${CLAUDE_SKILL_DIR}/prompts/persona_analyzer.md` 分析人格层
2. 参考 `${CLAUDE_SKILL_DIR}/prompts/content_brain_analyzer.md` 分析内容大脑层
3. 参考 `${CLAUDE_SKILL_DIR}/prompts/production_style_analyzer.md` 分析生产风格层
4. 参考 `${CLAUDE_SKILL_DIR}/prompts/brand_guardrails_analyzer.md` 分析品牌边界层

每层分析完后，输出关键发现，询问用户确认或补充。

### Step 4：生成四层文件

分析确认后，依次生成：

1. 参考 `${CLAUDE_SKILL_DIR}/prompts/persona_builder.md` → 写入 `./ups/{slug}/persona.md`
2. 参考 `${CLAUDE_SKILL_DIR}/prompts/content_brain_builder.md` → 写入 `./ups/{slug}/content_brain.md`
3. 参考 `${CLAUDE_SKILL_DIR}/prompts/production_style_builder.md` → 写入 `./ups/{slug}/production_style.md`
4. 参考 `${CLAUDE_SKILL_DIR}/prompts/brand_guardrails_builder.md` → 写入 `./ups/{slug}/brand_guardrails.md`

### Step 5：合并生成组合 Skill

参考 `${CLAUDE_SKILL_DIR}/prompts/merger.md`，将四层合并为 `./ups/{slug}/SKILL.md`。

同时写入 `./ups/{slug}/meta.json`：

```json
{
  "name": "{name}",
  "slug": "{slug}",
  "platform": "{platform}",
  "domain": "{domain}",
  "version": "1.0.0",
  "created_at": "{ISO8601}",
  "updated_at": "{ISO8601}",
  "source_materials": ["字幕", "评论区"],
  "layers": ["persona", "content_brain", "production_style", "brand_guardrails"]
}
```

### Step 6：确认与交付

生成完成后，展示可用的子 Skill 列表：

```
✅ {name} 的数字分身已生成，可用指令：

  /{slug}              → 像他聊天（陪伴/问答）
  /{slug}-brainstorm   → 像他做选题会
  /{slug}-script       → 像他写口播脚本
  /{slug}-comment      → 像他回复评论区
  /{slug}-live         → 像他接直播弹幕
  /{slug}-brand        → 检查内容像不像他 / 会不会翻车
```

---

## 子 Skill 行为规范

### /{slug}（陪伴聊天）

激活后，完全以该 UP 主的 Persona 层运行：
- 用他的口头禅、语气、节奏回复
- 遇到不在 Content Brain 范围内的话题，用他的方式回避或表态
- 不跳出角色，不说"作为 AI"

### /{slug}-brainstorm（选题会）

输入：一个方向/关键词/热点
输出：
1. 他会不会做这个选题（判断 + 理由）
2. 他会从什么角度切入
3. 3 个他风格的标题候选
4. 开头 hook 怎么下

### /{slug}-script（口播脚本）

输入：选题 + 核心观点
输出：按他的 Production Style 写一版口播脚本，包含：
- 开头 hook（前 15 秒）
- 主体结构（分段 + 金句密度）
- 结尾 CTA

### /{slug}-comment（评论区回复）

输入：一条或多条评论
输出：按他的风格逐条回复，区分：
- 正常提问
- 质疑/杠精
- 夸奖
- 无意义水评

### /{slug}-live（直播弹幕）

输入：一批弹幕（逐行）
输出：他会接哪些、怎么接、哪些忽略、哪些会引发互动

### /{slug}-brand（品牌检查）

输入：一段文案/脚本/标题
输出：
1. 像不像他（0-10 分 + 理由）
2. 哪里不像
3. 有没有翻车风险
4. 修改建议

---

## 进化模式：追加素材

当用户说"我有新素材"：

1. 询问素材类型（字幕/评论/直播/描述）
2. 解析新素材
3. 判断哪些层需要更新
4. 用 `Edit` 工具追加到对应文件
5. 重新生成 `SKILL.md`（merger）
6. 更新 `meta.json` 版本号和 updated_at

---

## 进化模式：对话纠错

当用户说"这不对" / "他不会这样说"：

1. 参考 `${CLAUDE_SKILL_DIR}/prompts/correction_handler.md` 识别纠错内容
2. 判断属于哪一层（Persona / Content Brain / Production Style / Brand Guardrails）
3. 生成纠错记录
4. 用 `Edit` 工具追加到对应文件的 `## Correction 记录` 区块
5. 重新生成 `SKILL.md`

---

## 管理指令

`/list-ups`:
```bash
python3 ${CLAUDE_SKILL_DIR}/tools/skill_writer.py --action list --base-dir ./ups
```

`/delete-up {slug}`:
确认后执行：
```bash
rm -rf ups/{slug}
```
