---
name: delete-up
description: "删除已生成的 UP 主 Skill | Delete a generated UP skill"
argument-hint: "<slug>"
user-invocable: true
allowed-tools: Bash, Read
---

> **语言**: 根据用户第一条消息的语言，全程使用同一语言回复。

# /delete-up — 删除 UP 主 Skill

## 触发条件

当用户说 `/delete-up {slug}` 或"删除 XX 的 skill"时启动。

## 执行流程

1. 读取 `{{UPS_DIR}}/{slug}/meta.json` 确认 UP 主存在，展示基本信息
2. 明确询问用户确认删除（不可恢复）
3. 用户确认后执行：
   ```bash
   rm -rf {{UPS_DIR}}/{slug}
   ```
4. 提示删除完成
