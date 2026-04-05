---
name: update-up
description: "更新已有 UP 主 Skill（追加素材/纠错） | Update an existing UP skill with new materials"
argument-hint: "<slug>"
user-invocable: true
allowed-tools: Bash, Read, Write, Edit
---

> **语言**: 根据用户第一条消息的语言，全程使用同一语言回复。

# /update-up — 更新 UP 主 Skill

## 触发条件

当用户说 `/update-up {slug}` 或"更新 XX 的 skill"时启动。

## 执行流程

1. 读取 `{{UPS_DIR}}/{slug}/meta.json` 确认 UP 主存在
2. 询问更新类型：
   - 追加新素材（字幕/评论/直播/描述）
   - 对话纠错（"他不会这样说"）
3. 归档当前版本：
   ```bash
   uv run --directory {{UPS_DIR}}/up-skill python3 tools/skill_writer.py --action archive --slug {slug} --base-dir {{UPS_DIR}}
   ```
4. 执行更新（参考 create-up 的分析流程）
5. 递增版本号：
   ```bash
   uv run --directory {{UPS_DIR}}/up-skill python3 tools/skill_writer.py --action version --slug {slug} --base-dir {{UPS_DIR}}
   ```
