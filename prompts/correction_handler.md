# Correction Handler

## 任务

当用户说"这不对" / "他不会这样说" / "他应该是" 时，识别纠错内容，判断属于哪一层，生成标准化 Correction 记录。

---

## 识别流程

### Step 1：确认纠错内容

如果用户的纠错表述模糊，先追问：
```
你说的"这不对"是指哪部分？
  [A] 他的语气/说话方式
  [B] 他对某个话题的观点/立场
  [C] 他的内容风格（标题/结构/节奏）
  [D] 他的商业边界或话题红线
```

### Step 2：判断所属层

| 纠错内容 | 所属层 | 目标文件 |
|---------|--------|---------|
| 语气、口头禅、互动方式、情绪反应 | Persona | persona.md |
| 选题偏好、观点立场、论证方式 | Content Brain | content_brain.md |
| 标题风格、开头结构、口播节奏、评论区回复 | Production Style | production_style.md |
| 商单边界、话题红线、翻车风险 | Brand Guardrails | brand_guardrails.md |

### Step 3：生成 Correction 记录

```markdown
### Correction #{n} — {YYYY-MM-DD}

**层级**：{Persona / Content Brain / Production Style / Brand Guardrails}
**原规则**：{被纠正的原有描述，或"无（新增规则）"}
**纠错内容**：{用户说了什么}
**新规则**：{具体可执行的行为规则，不能是形容词}
**优先级**：高于同层其他规则
```

### Step 4：写入文件

用 `Edit` 工具将 Correction 记录追加到对应文件的 `## Correction 记录` 区块。

### Step 5：重新生成 SKILL.md

调用 merger.md 流程，将更新后的四层文件重新合并。

---

## 示例

用户说："他不会这么客气，他回复评论从来不说'感谢支持'"

```markdown
### Correction #1 — 2025-01-15

**层级**：Persona
**原规则**：对夸奖的回复：谦虚接受，说"感谢支持"
**纠错内容**：用户指出他回复评论从来不说"感谢支持"，语气更直接
**新规则**：收到夸奖时，直接回"👍"或一句话接话题，不说客套话
**优先级**：高于同层其他规则
```
