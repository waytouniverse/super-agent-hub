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
│  routes/chat_ws.py:  /ws/chat/{engine} 单引擎聊天  │
│  routes/team_ws.py:  /ws/chat/team  多引擎团队     │
│  routes/sessions.py: /api/sessions 会话CRUD       │
│  routes/stats.py:     /api/stats    Token统计     │
│  routes/engines.py:   /api/engines  引擎检测       │
│  routes/projects.py:  /api/projects 项目目录       │
│  routes/files.py:     /api/files   文件操作        │
│  adapters/: 引擎适配器（子进程调用CLI）            │
│  orchestrator/: 多引擎编排子包（4种模式）          │
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
│  pages/: ChatPage, TeamChatPage, SessionsPage,    │
│          StatsPage, HomePage, SettingsPage         │
│  hooks/: useWebSocket, useTeamSession,            │
│          useEngines, useStats                      │
│  components/: MessageBubble, ToolCallCard,        │
│    ChatInput, SessionList, Sidebar, Layout,        │
│    team/{ModeSelector, ModeConfigPanel},           │
│    parallel/ParallelView,                          │
│    debate/{DebateView, JudgeCard},                 │
│    consultation/{ConsultationView,                 │
│      PlanConfirmationPanel, TaskExecutionPanel}    │
└───────────────────────────────────────────────────┘
```

### 关键设计决策

- **一切通过子进程**：后端不直接调用 API，而是启动引擎的 CLI 子进程，解析其 JSON/JSONL 输出
- **适配器模式**：每个引擎实现 `BaseAdapter`（`build_command` + `chat_stream` + `parse_usage`），统一输出 `MessageChunk`（type: text/tool_call/done/error）
- **WebSocket 是核心通道**：前端通过 WebSocket 接收流式文本/工具调用/错误事件，REST API 只用于元数据
- **Codex 桌面版优先**：detector 优先检测 `/Applications/Codex.app/Contents/Resources/codex`，适配器自动注入 macOS 系统代理

### 团队模式：4 种协作方式

团队模式已从单一串行审查升级为 4 种模式，由 `orchestrator/` 子包实现：

| 模式 | 类 | 流程 |
|------|-----|------|
| **串行审查** (serial) | `SerialOrchestrator` | 引擎 1→2→3 依次发言，后一个能看到前一个的输出 |
| **并行讨论** (parallel) | `ParallelOrchestrator` | 所有引擎同时独立回答同一 prompt（`asyncio.gather`） |
| **多轮辩论** (debate) | `DebateOrchestrator` | 每轮所有引擎并行发言→裁判评估（CONTINUE/CONCLUDE）→下一轮 |
| **会诊执行** (consultation) | `ConsultationOrchestrator` | 辩论→生成行动计划→用户确认→引擎自动执行任务 |

工厂函数 `create_orchestrator(mode, engines, cwd, config)` 根据 mode 创建对应编排器。
旧的 `orchestrator.py` 保留为兼容导入层，`TeamOrchestrator` 指向 `SerialOrchestrator`。

### 前端架构要点

- **TeamChatPage** 根据 mode 路由到不同视图：serial→SerialMessageList，parallel→ParallelView，debate→DebateView，consultation→ConsultationView
- **useTeamSession** hook 管理所有团队模式共享状态：消息列表、流式内容（`Record<engine, string>`）、轮次、阶段、计划、任务
- **INTERNAL_EVENT_TYPES** 模式：`task_start/task_done/task_error/plan_generated/phase_start/phase_end` 事件需持久化到 DB（用于会话恢复），但**不在聊天界面渲染为文本消息**。所有视图组件都有 `hasVisibleMessageContent()` 过滤
- **IME composition guard**：ChatInput 中 `e.nativeEvent.isComposing || e.keyCode === 229` 阻止中文输入法 Enter 误发送
- **会话恢复**：从 DB 读取 messages 后重建 plan/tasks/phase 状态，仅在 `s.status === 'interrupted'` 时将运行中任务标记为 error

### 后端重要模式

- **Token 累加而非覆盖**：`update_session()` 时必须 `prev.get("total_xxx", 0) + new_value`，支持多轮对话
- **config.load() 必须 deepcopy**：`DEFAULT_CONFIG` 含嵌套 dict，浅拷贝会导致全局状态被修改
- **会话删除先删 FK 行**：`token_events` 没有 ON DELETE CASCADE，必须先 `DELETE FROM token_events` 再删 session
- **permission_mode 每次请求显式重置**：不依赖默认值，避免上一次请求的值残留

## 常用命令

### 开发环境

```bash
# 后端（使用 venv）
cd agent-hub
./venv/bin/python -m agent_hub.main

# 前端（开发服务器，端口 3000）
cd agent-hub/frontend && npm run dev
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
gh release create v0.3.0 \
  --repo waytouniverse/super-agent-hub \
  --title "Super Agent Hub v0.3.0 - 标题" \
  --notes "更新说明" \
  "Agent Hub_0.3.0_aarch64.dmg"
```

## 数据存储

- 配置：`~/.agent-hub/config.json`
- 数据库：`~/.agent-hub/data/sessions.db`（SQLite，WAL 模式，外键 ON）
- **sessions 表**：会话元数据（engine、model、title、status、cwd、team_mode、team_config、token 统计）
- **messages 表**：每条消息（role、type、content、tool_name、tool_input、sequence、engine_name、phase、round、plan）
- **token_events 表**：每次对话的 token 消耗记录（session_id、model、input/output/cache tokens、cost_usd）
- **session_aliases 表**：会话别名映射（用于向前兼容）

## 引擎适配器开发

实现新引擎需要：

1. 在 `detector.py` 的 `ENGINE_DEFINITIONS` 中添加入口
2. 创建 `adapters/xxx.py`，继承 `BaseAdapter`，实现：
   - `build_command(prompt, session_id, cwd)` → `list[str]`
   - `chat_stream(...)` → `AsyncIterator[MessageChunk]`（type: text/tool_call/done/error）
   - `parse_usage(raw_data)` → `dict`（input_tokens/output_tokens/cache_read/cache_write）
3. 在 `orchestrator/base.py` 和 `routes/chat_ws.py` 的 `ADAPTER_MAP` 中注册
4. 在 `stats.py` 的 `PRICING` 中添加模型定价

## Tauri 桌面壳

`src-tauri/src/main.rs`：
- 启动时 pkill 残留的 `agent-hub-backend` 进程
- 找到 PyInstaller 打包的 backend 二进制（macOS .app bundle 的 Resources 目录）
- `spawn()` 启动后端，轮询 TCP 连接直到 9527 可用（最多 15s）
- 打开无边框 Webview，直接嵌入 `http://127.0.0.1:9527`
- 窗口关闭时 `child.kill()` 清理后端进程
