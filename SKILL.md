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

### 创建模式
当用户说以下任意内容时启动：
- `/create-up`
- "帮我创建一个 UP 主 skill"
- "我想蒸馏一个 UP 主"
- "给我做一个 XX 的 skill"

### 激活模式（对话内调用已生成的 UP 主）
当用户说 `/{slug}` 或 `/{slug} + 任意自然语言` 时：
1. 在 `{{UPS_DIR}}/` 目录下查找 `{slug}/SKILL.md`
2. 如果找到，用 `Read` 工具读取该 SKILL.md 的完整内容
3. 将内容注入当前对话上下文，根据用户的自然语言意图自动匹配对应行为（聊天、选题、写脚本、风格检查等）
4. 如果未找到，提示用户该 UP 主尚未生成，建议运行 `/create-up`

### 进化模式
当用户对已有 UP 主 Skill 说以下内容时，进入进化模式：
- "我有新素材" / "追加"
- "这不对" / "他不会这样说" / "他应该是"
- `/update-up {slug}`

### 管理模式
管理命令已拆为独立 Skill，无需在此处处理。用户可直接使用 `/list-ups`、`/update-up`、`/delete-up`。

---

## 工具使用规则

| 任务 | 使用工具 |
|------|---------|
| 读取字幕文件（.srt/.vtt/.txt） | `Read` 工具 |
| 读取截图/封面图 | `Read` 工具（原生支持图片） |
| 解析 B 站字幕 JSON | `Bash` → `uv run --directory ${SKILL_DIR} python3 tools/subtitle_parser.py` |
| 解析评论区导出 | `Bash` → `uv run --directory ${SKILL_DIR} python3 tools/comment_parser.py` |
| 写入/更新 Skill 文件 | `Write` / `Edit` 工具 |
| 列出已有 Skill | 使用独立 Skill `/list-ups` |

**基础目录**：Skill 文件写入 `{{UPS_DIR}}/{slug}/`。

> ⚠️ **路径警告**：所有生成的文件必须写入 `{{UPS_DIR}}/{slug}/` 目录。
> 不要写入项目源码目录或 `${SKILL_DIR}` 下的任何子目录。
> `${SKILL_DIR}` 是工具代码所在目录，不是输出目录。输出目录是 `{{UPS_DIR}}/`。

---

## 主流程：创建新 UP 主 Skill

### Step 1：基础信息录入（3 个问题）

参考 `${SKILL_DIR}/prompts/intake.md` 的问题序列，只问 3 个问题：

1. **UP 主名/代号**（必填）
2. **基本信息**（一句话：平台、领域、粉丝量级、性别）
   - 示例：`B 站 科技区 百万粉 男`
3. **人设画像**（一句话：风格标签、个性、印象）
   - 示例：`毒舌 反消费主义 爱用数据说话 评论区互动很多`

除名字外均可跳过。收集完后汇总确认再进入下一步。

### Step 2：原材料导入

**智能识别用户输入**：先检查用户在触发时是否已附带素材信息，自动判断类型并跳过选择菜单：

| 用户输入 | 自动识别为 | 动作 |
|---------|-----------|------|
| `space.bilibili.com` 链接（或含该域名的搜索页 URL） | [E] 主页采集 | 直接进入自动采集流程 |
| 一个或多个 `bilibili.com/video/` 链接 | [E] 视频链接采集 | 以 `--urls` 模式调用 collector |
| 本地文件夹路径或 .srt / .vtt / .txt 文件路径 | [A] 字幕文件 | 直接读取文件 |
| 粘贴的逐字稿文本 | [A] 字幕文本 | 直接作为素材 |
| 描述了 UP 主风格特征的文字 | [D] 手动描述 | 直接作为素材 |

**仅当用户未提供任何素材信息时**，才展示五种方式供选择：

```
原材料怎么提供？

  [A] 字幕文件
      上传 .srt / .vtt / .txt 字幕，或直接粘贴逐字稿

  [B] 评论区导出
      上传评论区 CSV/JSON，或粘贴 UP 主的评论回复截图

  [C] 直播转录
      上传直播回放字幕或转录文本

  [D] 手动描述
      直接告诉我他的风格、口头禅、内容偏好

  [E] UP 主主页链接（推荐）
      给一个 B 站主页链接（space.bilibili.com/...），自动采集视频字幕
```

**[E] 自动采集流程**：
0. 如果 Step 1 尚未收集 UP 主名字，先询问名字（用于生成 slug），再继续采集
1. 先用 `--limit 1 --yes` 试探性调用 collector，从输出中获取频道视频总数
2. 告知用户视频总数，询问要采集几个（建议至少 5-10 个，默认 20）
3. 用户确认数量后，调用 `uv run --directory ${SKILL_DIR} python3 tools/collector.py --slug {slug} --space <url> --limit {用户指定数量} --yes`
4. collector 会用 yt-dlp 列出视频 → 优先抓官方字幕 → 无字幕则下载音频 ASR
5. ⏱ 采集耗时取决于视频数量和字幕可用性：有官方字幕时很快（几秒/条），需要 ASR 转录时约等于视频时长。20 条视频预计 5-15 分钟，请设置足够的 timeout（至少 600000ms）并耐心等待
6. 转录文本缓存到 `~/.up-skill/cache/{slug}/transcripts/`
7. 采集完成后读取缓存目录中的文本，进入 Step 3 分析

> ⚠️ **必须等待采集完成**：collector 输出中会显示 `[N/总数]` 进度。
> 只有看到 `✅ 采集完成：共获取 X/Y 个字幕文件` 这行最终汇总时，才代表采集结束。
> 中途的进度输出（如 `[7/20]`）不代表完成，不要提前进入 Step 3。

**最低要求**：至少提供 [A]、[D] 或 [E] 之一。原材料越多，四层分身越准确。

### Step 3：四层分析

收到原材料后，依次执行：

1. 参考 `${SKILL_DIR}/prompts/persona_analyzer.md` 分析人格层
2. 参考 `${SKILL_DIR}/prompts/content_brain_analyzer.md` 分析内容大脑层
3. 参考 `${SKILL_DIR}/prompts/production_style_analyzer.md` 分析生产风格层
4. 参考 `${SKILL_DIR}/prompts/brand_guardrails_analyzer.md` 分析品牌边界层

每层分析完后，输出关键发现，询问用户确认或补充。

### Step 4：生成四层文件

> ⚠️ **再次确认输出路径**：下面所有 `Write` 操作的目标路径必须是 `{{UPS_DIR}}/{slug}/`，不是 `${SKILL_DIR}/ups/` 或其他路径。

分析确认后，依次生成：

1. 参考 `${SKILL_DIR}/prompts/persona_builder.md` → 写入 `{{UPS_DIR}}/{slug}/persona.md`
2. 参考 `${SKILL_DIR}/prompts/content_brain_builder.md` → 写入 `{{UPS_DIR}}/{slug}/content_brain.md`
3. 参考 `${SKILL_DIR}/prompts/production_style_builder.md` → 写入 `{{UPS_DIR}}/{slug}/production_style.md`
4. 参考 `${SKILL_DIR}/prompts/brand_guardrails_builder.md` → 写入 `{{UPS_DIR}}/{slug}/brand_guardrails.md`

### Step 5：合并生成组合 Skill

参考 `${SKILL_DIR}/prompts/merger.md`，将四层合并为 `{{UPS_DIR}}/{slug}/SKILL.md`。

同时写入 `{{UPS_DIR}}/{slug}/meta.json`（注意：不是 `${SKILL_DIR}` 下）：

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

生成完成后，展示用法示例：

```
✅ {name} 的数字分身已生成！

用 /{slug} 调用，直接说你想做什么：

  /{slug} 最近有什么热点可以做？
  /{slug} 帮我写一期关于 XX 的口播脚本
  /{slug} 帮我看看这个标题行不行：《XXX》
```

---

## 能力说明

激活后，分身根据用户的自然语言意图自动匹配对应行为：

### 聊天/问答

完全以该 UP 主的 Persona 层运行：
- 用他的口头禅、语气、节奏回复
- 遇到不在 Content Brain 范围内的话题，用他的方式回避或表态
- 不跳出角色，不说"作为 AI"

### 选题分析

输入：一个方向/关键词/热点
输出：
1. 他会不会做这个选题（判断 + 理由）
2. 他会从什么角度切入
3. 3 个他风格的标题候选
4. 开头 hook 怎么下

### 写口播脚本

输入：选题 + 核心观点
输出：按他的 Production Style 写一版口播脚本，包含：
- 开头 hook（前 15 秒）
- 主体结构（分段 + 金句密度）
- 结尾 CTA

### 风格边界检查

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

1. 参考 `${SKILL_DIR}/prompts/correction_handler.md` 识别纠错内容
2. 判断属于哪一层（Persona / Content Brain / Production Style / Brand Guardrails）
3. 生成纠错记录
4. 用 `Edit` 工具追加到对应文件的 `## Correction 记录` 区块
5. 重新生成 `SKILL.md`
