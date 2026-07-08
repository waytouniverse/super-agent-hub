# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 用户偏好

- 所有回复使用中文
- 简洁直接，不啰嗦
- 不主动创建 README、文档、总结文件

## 项目架构

Agent Hub 是一个 **Tauri 桌面应用**，统一管理多个 AI Agent CLI 工具（Claude Code、Codex、Hermes）。

```
┌─ Tauri Shell (Rust) ─────────────────────────────┐
│  main.rs: 启动 PyInstaller 打包的 Python 后端     │
│  然后打开 Webview 指向 http://127.0.0.1:9527      │
│  窗口关闭时自动 kill 后端进程                      │
└───────────────────────────────────────────────────┘
         │ 启动子进程
         ▼
┌─ Python FastAPI 后端 (port 9527) ─────────────────┐
│  server.py: 注册路由、挂载前端静态资源             │
│  routes/chat_ws.py:  /ws/chat/{engine} 核心聊天   │
│  routes/team_ws.py:  /ws/chat/team  多引擎团队     │
│  routes/sessions.py: /api/sessions 会话CRUD       │
│  routes/stats.py:     /api/stats    Token统计     │
│  adapters/: 引擎适配器（子进程调用CLI）            │
│  orchestrator.py: 多引擎串行编排                   │
│  detector.py: 自动检测已安装引擎                    │
│  session_store.py: SQLite 会话/消息存储            │
│  stats.py: Token 定价模型                          │
│  config.py: ~/.agent-hub/config.json               │
└───────────────────────────────────────────────────┘
         │ 子进程调用 CLI
         ▼
┌─ AI Engine CLI 进程 ──────────────────────────────┐
│  Claude: claude -p --output-format stream-json    │
│  Codex:  codex exec --json (桌面版/CLI)           │
│  Hermes: hermes (预留)                             │
└───────────────────────────────────────────────────┘

┌─ React 前端 (Vite SPA) ───────────────────────────┐
│  WebSocket 流式聊天 | 会话历史 | Token 仪表盘      │
│  团队模式: 选择 2-3 引擎串行审查讨论               │
└───────────────────────────────────────────────────┘
```

### 关键设计决策

- **一切通过子进程**：后端不直接调用 API，而是启动引擎的 CLI 子进程，解析其 JSON/JSONL 输出
- **适配器模式**：每个引擎实现 `BaseAdapter`（`build_command` + `chat_stream` + `parse_usage`），统一输出 `MessageChunk`
- **WebSocket 是核心通道**：前端通过 WebSocket 接收流式文本/工具调用/错误事件，REST API 只用于元数据
- **团队模式是串行审查**：引擎 2 能看到引擎 1 的输出（作为 prompt 上下文），后一个审查前一个
- **Codex 桌面版优先**：detector 优先检测 `/Applications/Codex.app/Contents/Resources/codex`，适配器自动注入 macOS 系统代理

## 常用命令

### 开发环境

```bash
# 后端（使用 venv）
cd agent-hub
./venv/bin/python -m agent_hub.main

# 前端（开发服务器，端口 3000）
cd agent-hub/frontend && npm run dev

# 使用独立的前端开发服务器（代理到后端 9527）
# 前端 dev server 默认在 3000，直接访问 http://localhost:3000
```

### 构建与打包

```bash
# 一键构建：前端 + PyInstaller 后端 + Tauri DMG
bash scripts/build-all.sh

# 单独构建 PyInstaller 后端二进制
bash scripts/build-backend.sh

# 单独构建前端
cd frontend && npm run build

# DMG 输出位置
# src-tauri/target/release/bundle/dmg/Agent Hub_{version}_aarch64.dmg
```

### GitHub Release

```bash
# 创建 release 并上传 DMG
gh release create v0.2.0 \
  --repo waytouniverse/super-agent-hub \
  --title "Super Agent Hub v0.2.0 - 标题" \
  --notes "更新说明" \
  "Agent Hub_0.2.0_aarch64.dmg"
```

## 数据存储

- 配置：`~/.agent-hub/config.json`
- 数据库：`~/.agent-hub/data/sessions.db`（SQLite，WAL 模式）
- sessions 表：会话元数据（engine、model、title、token 统计、cwd）
- messages 表：每条消息（role、type、content、tool_name、`engine_name` 用于团队模式）
- token_events 表：每次对话的 token 消耗记录

## 引擎适配器开发

实现新引擎需要：

1. 在 `detector.py` 的 `ENGINE_DEFINITIONS` 中添加入口
2. 创建 `adapters/xxx.py`，继承 `BaseAdapter`，实现三个方法：
   - `build_command(prompt, session_id, cwd)` → `list[str]`
   - `chat_stream(...)` → `AsyncIterator[MessageChunk]`（type: text/tool_call/done/error）
   - `parse_usage(raw_data)` → `dict`（input_tokens/output_tokens/cache_read/cache_write）
3. 在 `orchestrator.py` 和 `chat_ws.py` 的 `ADAPTER_MAP` 中注册

MessageChunk 类型约定：
- `text`: `MessageChunk("text", content="...")` — 会被前端流式展示和持久化
- `tool_call`: `MessageChunk("tool_call", tool="...", input={...})`
- `done`: `MessageChunk("done", input_tokens=0, output_tokens=0, ...)` — 表示当前 turn 结束
- `error`: `MessageChunk("error", content="...")`

## Tauri 桌面壳

`src-tauri/src/main.rs`：
- 启动时 pkill 残留的 `agent-hub-backend` 进程
- 找到 PyInstaller 打包的 backend 二进制（macOS .app bundle 的 Resources 目录）
- `spawn()` 启动后端，轮询 TCP 连接直到 9527 可用（最多 15s）
- 打开无边框 Webview，直接嵌入 `http://127.0.0.1:9527`
- 窗口关闭时 `child.kill()` 清理后端进程
- `tauri.conf.json` 的 `bundle.resources` 包含 `pyinstaller-dist/agent-hub-backend`
