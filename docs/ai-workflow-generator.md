# AI Workflow Generator 开发文档

## 概述

AI Workflow Generator 是 FastGPT 的智能工作流生成系统，通过自然语言描述自动生成工作流，支持动态插件开发。用户可以通过对话方式创建、优化和扩展工作流。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FastGPT Platform                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                   AI Workflow Engine (NEW)                         │   │
│  │                                                                   │   │
│  │   User Input → OpenCode API → Generate Workflow + Plugins       │   │
│  │                                                                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                   Plugin Registry (NEW)                            │   │
│  │                                                                   │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │   │
│  │   │ Plugin Meta  │  │ Source Code │  │ API Spec    │         │   │
│  │   │ (name,desc) │  │(TypeScript) │  │ (OpenAPI)   │         │   │
│  │   └─────────────┘  └─────────────┘  └─────────────┘         │   │
│  │                                                                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              Plugin Runtime (NEW) - 独立 API 服务                │   │
│  │                                                                   │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │   │
│  │   │  Plugin 1   │  │  Plugin 2   │  │  Plugin N   │         │   │
│  │   │  :3001      │  │  :3002      │  │  :300N      │         │   │
│  │   └─────────────┘  └─────────────┘  └─────────────┘         │   │
│  │                                                                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              Workflow Engine                                       │   │
│  │    Nodes can call Plugins via HTTP                                │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

外部服务:
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│   OpenCode API  │  │  OpenSandbox  │  │    FastGPT     │
│   (独立服务)     │  │   (验证)       │  │    Sandbox     │
└────────────────┘  └────────────────┘  └────────────────┘
```

## 核心设计决策

| 方面 | 实现 |
|------|------|
| 大脑 | OpenCode API 独立服务 |
| 插件代码存储 | 持久化 + 独立 API 服务 |
| 用户交互 | 多轮交互确认 |
| 工作流生成 | 从 0 生成 + 优化现有 |
| 验证 | OpenSandbox 验证 |

## 技术栈

- **后端**: Python FastAPI, MongoDB, Redis
- **前端**: React, Chakra UI, TypeScript
- **数据库**: MongoDB (PostgreSQL/pgvector)
- **外部服务**: OpenCode API, OpenSandbox

## 快速开始

### 1. 环境要求

- Node.js >= 20
- pnpm >= 9.15.9
- Python >= 3.10
- Docker & Docker Compose

### 2. 配置环境变量

```bash
# .env
MONGODB_URI=mongodb://username:password@localhost:27017/fastgpt
REDIS_URL=redis://localhost:6379
OPENCODE_API_URL=http://localhost:8080
OPENCODE_API_KEY=your-api-key
```

### 3. 启动 OpenCode API 服务

```bash
# 启动 OpenCode API 服务（独立部署）
# 详见 OpenCode 官方文档
```

### 4. 启动 FastGPT

```bash
pnpm install
pnpm dev
```

## API 文档

### 1. AI 对话接口 (生成/优化工作流)

**POST** `/api/core/workflow/ai/chat`

请求:
```json
{
  "teamId": "team_xxx",
  "message": "创建一个简单的工作流，包含聊天节点",
  "sessionId": "optional_session_id",
  "context": {
    "mode": "create",
    "workflowId": "optional_existing_workflow_id"
  }
}
```

响应:
```json
{
  "sessionId": "session_xxx",
  "message": "工作流已生成",
  "status": "ready",
  "workflowPreview": {
    "nodes": [...],
    "edges": [...]
  },
  "questions": [
    {
      "id": "q1",
      "question": "你希望工作流支持哪些功能？",
      "options": ["仅对话", "知识库", "工具调用"]
    }
  ]
}
```

### 2. 确认/回答问题

**POST** `/api/core/workflow/ai/workflow/confirm`

请求:
```json
{
  "sessionId": "session_xxx",
  "answer": "我选择知识库功能",
  "confirmed": false
}
```

响应:
```json
{
  "sessionId": "session_xxx",
  "status": "ready",
  "message": "工作流已生成",
  "workflow": {
    "nodes": [...],
    "edges": [...]
  }
}
```

### 3. 验证工作流

**POST** `/api/core/workflow/ai/workflow/validate`

请求:
```json
{
  "workflow": {
    "nodes": [...],
    "edges": [...]
  },
  "plugins": [
    {
      "name": "custom-plugin",
      "code": "..."
    }
  ]
}
```

响应:
```json
{
  "valid": true,
  "errors": [],
  "suggestions": ["建议添加错误处理节点"]
}
```

### 4. 获取可用节点

**GET** `/api/core/workflow/ai/nodes?teamId=xxx`

### 5. 创建工作流

**POST** `/api/core/workflow/ai/workflow/create`

```json
{
  "teamId": "team_xxx",
  "name": "My Workflow",
  "nodes": [
    {"id": "start", "flowNodeType": "workflowStart"},
    {"id": "chat", "flowNodeType": "chatNode"}
  ],
  "edges": [
    {"source": "start", "target": "chat"}
  ]
}
```

### 6. 插件管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/core/workflow/ai/plugin` | 列出插件 |
| POST | `/api/core/workflow/ai/plugin` | 创建插件 |
| PUT | `/api/core/workflow/ai/plugin/:id` | 更新插件 |
| DELETE | `/api/core/workflow/ai/plugin/:id` | 删除插件 |

## 项目结构

```
projects/opencode-agent/
├── src/
│   ├── agent/
│   │   ├── core.py              # WorkflowAgent 核心逻辑
│   │   ├── intent_analyzer.py   # 意图分析
│   │   ├── workflow_generator.py # 工作流生成
│   │   └── error_handler.py     # 错误处理
│   ├── tools/
│   │   ├── fastgpt.py           # FastGPT API 客户端
│   │   ├── storage.py           # 存储
│   │   └── queue.py             # 任务队列
│   ├── services/
│   │   ├── workflow_builder.py   # 工作流构建器
│   │   ├── plugin_code_generator.py # 插件代码生成
│   │   ├── plugin_manager.py    # 插件管理
│   │   └── component_registry.py # 组件注册表
│   └── api/
│       └── routes.py            # FastAPI 路由

packages/global/openapi/core/workflow/ai/
├── api.d.ts                    # 对话 API Schema (已更新)
└── plugin.d.ts                 # 插件 API Schema

packages/service/core/workflow/ai/
├── sessionSchema.ts            # Session MongoDB Schema
├── sessionController.ts         # Session CRUD
├── pluginSchema.ts             # Plugin MongoDB Schema
└── pluginController.ts         # Plugin CRUD

projects/app/src/pages/api/core/workflow/ai/
├── chat.ts                     # AI 对话 API (已更新)
├── nodes.ts                    # 获取可用节点
├── workflow/
│   ├── create.ts              # 创建工作流
│   ├── confirm.ts             # 确认/回答 (新增)
│   └── validate.ts            # 验证工作流 (新增)
└── plugin/
    ├── index.ts                # 插件列表/创建
    └── [pluginId].ts           # 插件更新/删除

packages/web/components/core/aiWorkflow/
├── AIWorkflowChat.tsx          # 对话界面组件 (已更新)
├── WorkflowPreview.tsx         # 工作流预览
├── api.ts                     # 前端 API 调用 (已更新)
└── index.ts                   # 导出
```

## 开发指南

### 添加新的 AI 能力

1. 修改 `projects/opencode-agent/src/agent/core.py`
2. 在 `WorkflowAgent` 类中添加新方法
3. 更新 API Schema (`packages/global/openapi/core/workflow/ai/api.d.ts`)
4. 更新前端 API 调用 (`packages/web/components/core/aiWorkflow/api.ts`)

### 添加新的节点类型

1. 在 FastGPT 核心中添加节点定义
2. 更新 `nodes.ts` API 返回新节点
3. 在前端 `WorkflowPreview.tsx` 中添加渲染逻辑

### 运行测试

```bash
# Python 测试
cd projects/opencode-agent
python3 -m pytest

# TypeScript 测试
pnpm test

# 集成测试
pnpm test test/integration/aiWorkflow.test.ts
```

## 部署

### Docker Compose

```yaml
services:
  opencode-api:
    image: opencode-api:latest
    ports:
      - "8080:8080"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}

  fastgpt:
    image: fastgpt/fastgpt:latest
    ports:
      - "3000:3000"
    environment:
      - OPENCODE_API_URL=http://opencode-api:8080
      - OPENCODE_API_KEY=${OPENCODE_API_KEY}
```

## 工作流生成模式

| 模式 | 说明 | Context 参数 |
|------|------|-------------|
| **从 0 生成** | 用户描述需求 → OpenCode 生成完整工作流 | `mode: "create"` |
| **优化现有** | 用户选择现有工作流 + 修改意图 → OpenCode 生成修改后的工作流 | `mode: "optimize"`, `workflowId: "xxx"` |

## 高级模式特性

1. **自动验证**：生成后通过 OpenSandbox 测试运行
2. **自动修复**：验证失败时自动重新生成
3. **多方案**：提供多个备选方案供用户选择
4. **预览编辑**：生成后可预览、修改后再发布

## 常见问题

### Q: OpenCode API 无法连接
A: 检查 `OPENCODE_API_URL` 环境变量，确保服务正常运行

### Q: MongoDB 连接失败
A: 验证 `MONGODB_URI` 格式，检查用户名密码

### Q: 工作流创建失败
A: 查看日志确认节点数据格式是否正确

### Q: 多轮交互如何工作？
A: 当 OpenCode API 返回 `status: "need_more_info"` 和 `questions` 时，前端显示问题，用户回答后调用 `/confirm` API

---

## 当前实现状态 (2026-02-24)

### 已完成

| 组件 | 状态 | 文件 |
|------|------|------|
| OpenCode Agent (Python) | ✅ 完成 | `projects/opencode-agent/` |
| FastGPT Backend API | ✅ 完成 | `projects/app/src/pages/api/core/workflow/ai/` |
| 前端组件 | ✅ 完成 | `packages/web/components/core/aiWorkflow/` |
| 插件管理 | ✅ 完成 | CRUD API |
| 工作流创建 | ✅ 完成 | `/workflow/create` |
| 多轮交互确认 | ✅ 完成 | `/workflow/confirm` |
| 工作流验证 | ✅ 完成 | `/workflow/validate` |
| 类型定义 | ✅ 完成 | `packages/global/openapi/core/workflow/ai/api.d.ts` |
| 安全修复 | ✅ 完成 | 深度限制、变量冲突、并发控制 |

### 待实现

| 组件 | 状态 | 说明 |
|------|------|------|
| OpenCode API 服务部署 | ⏳ 待部署 | 需要单独部署 |
| OpenSandbox 集成 | ⏳ 待集成 | 代码验证 |
| Plugin Runtime | ⏳ 规划中 | 独立 API 服务运行插件 |

### 环境变量

```bash
OPENCODE_API_URL=http://opencode-api:8080
OPENCODE_API_KEY=your-api-key
```

## 相关文档

- [FastGPT 官方文档](https://doc.fastgpt.cn)
- [OpenCode 官方文档](https://opencode.dev)
- [OpenSandbox GitHub](https://github.com/alibaba/OpenSandbox)
