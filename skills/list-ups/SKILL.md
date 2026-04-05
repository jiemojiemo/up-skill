---
name: list-ups
description: "列出所有已生成的 UP 主 Skill | List all generated UP skills"
user-invocable: true
allowed-tools: Bash, Read
---

> **语言**: 根据用户第一条消息的语言，全程使用同一语言回复。

# /list-ups — 列出已生成的 UP 主

## 触发条件

当用户说 `/list-ups` 或"列出所有 UP 主"时启动。

## 执行

```bash
uv run --directory {{UPS_DIR}}/up-skill python3 tools/skill_writer.py --action list --base-dir {{UPS_DIR}}
```

如果没有任何 UP 主，提示用户使用 `/create-up` 创建第一个。
