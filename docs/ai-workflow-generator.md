# AI Workflow Generator 开发文档

## 概述

AI Workflow Generator 是一个 FastGPT 插件，通过自然语言描述自动生成工作流。用户可以通过对话方式创建、优化和扩展工作流。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      FastGPT Frontend                       │
│  (AIWorkflowChat Component)                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastGPT Backend API                       │
│  /api/core/workflow/ai/*                                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  OpenCode Agent Service                     │
│  (Python FastAPI)                                           │
│  - Intent Analysis                                          │
│  - Workflow Generation                                      │
│  - Code Storage (MinIO)                                     │
│  - Task Queue (Redis)                                       │
└─────────────────────────────────────────────────────────────┘
```

## 技术栈

- **后端**: Python FastAPI, MongoDB, Redis, MinIO
- **前端**: React, Chakra UI, TypeScript
- **数据库**: MongoDB (PostgreSQL/pgvector)
- **消息队列**: Redis
- **对象存储**: MinIO

## 快速开始

### 1. 环境要求

- Node.js >= 20
- pnpm >= 9.15.9
- Python >= 3.10
- Docker & Docker Compose

### 2. 启动依赖服务

```bash
# 启动 MongoDB, Redis, MinIO
docker run -d --name mongo -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=myusername \
  -e MONGO_INITDB_ROOT_PASSWORD=mypassword \
  mongo:5.0.32

docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### 3. 配置环境变量

```bash
# .env
MONGODB_URI=mongodb://myusername:mypassword@localhost:27017/fastgpt
REDIS_URL=redis://localhost:6379
OPENCODE_AGENT_URL=http://localhost:8080
```

### 4. 启动 OpenCode Agent

```bash
cd projects/opencode-agent
docker build -t fastgpt-opencode-agent .
docker run -d -p 8080:8080 \
  -e FASTGPT_BASE_URL=http://host.docker.internal:3000 \
  fastgpt-opencode-agent
```

### 5. 启动 FastGPT

```bash
pnpm install
pnpm dev
```

## API 文档

### 1. AI 对话接口

**POST** `/api/core/workflow/ai/chat`

```json
{
  "teamId": "team_xxx",
  "message": "创建一个简单的工作流，包含聊天节点",
  "sessionId": "optional_session_id",
  "context": {
    "mode": "create"
  }
}
```

响应:
```json
{
  "sessionId": "session_xxx",
  "message": "已生成工作流",
  "workflowPreview": {
    "nodes": [...],
    "edges": [...]
  }
}
```

### 2. 获取可用节点

**GET** `/api/core/workflow/ai/nodes?teamId=xxx`

### 3. 创建工作流

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

### 4. 插件管理

- `GET /api/core/workflow/ai/plugin` - 列出插件
- `POST /api/core/workflow/ai/plugin` - 创建插件
- `PUT /api/core/workflow/ai/plugin/:id` - 更新插件
- `DELETE /api/core/workflow/ai/plugin/:id` - 删除插件

## 项目结构

```
projects/opencode-agent/
├── src/
│   ├── agent/
│   │   └── core.py          # WorkflowAgent 核心逻辑
│   ├── tools/
│   │   ├── fastgpt.py       # FastGPT API 客户端
│   │   ├── storage.py       # MinIO/MongoDB 存储
│   │   └── queue.py         # Redis 任务队列
│   └── api/
│       └── routes.py        # FastAPI 路由
├── Dockerfile
└── pyproject.toml

packages/global/openapi/core/workflow/ai/
├── api.d.ts                 # 对话 API Schema
└── plugin.d.ts              # 插件 API Schema

packages/service/core/workflow/ai/
├── sessionSchema.ts         # Session MongoDB Schema
├── sessionController.ts     # Session CRUD
├── pluginSchema.ts          # Plugin MongoDB Schema
└── pluginController.ts      # Plugin CRUD

projects/app/src/pages/api/core/workflow/ai/
├── chat.ts                  # AI 对话 API
├── nodes.ts                 # 获取可用节点
├── workflow/create.ts       # 创建工作流
└── plugin/
    ├── index.ts             # 插件列表/创建
    └── [pluginId].ts        # 插件更新/删除

packages/web/components/core/aiWorkflow/
├── AIWorkflowChat.tsx       # 对话界面组件
├── WorkflowPreview.tsx       # 工作流预览
├── api.ts                   # 前端 API 调用
└── index.ts                 # 导出
```

## 开发指南

### 添加新的 AI 能力

1. 修改 `projects/opencode-agent/src/agent/core.py`
2. 在 `WorkflowAgent` 类中添加新方法
3. 更新 API Schema (`packages/global/openapi/core/workflow/ai/api.d.ts`)
4. 添加前端组件

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
  opencode-agent:
    image: fastgpt/opencode-agent:latest
    ports:
      - "8080:8080"
    environment:
      - FASTGPT_BASE_URL=http://fastgpt:3000
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - fastgpt
```

## 常见问题

### Q: OpenCode Agent 无法连接
A: 检查 `OPENCODE_AGENT_URL` 环境变量，确保服务正常运行

### Q: MongoDB 连接失败
A: 验证 `MONGODB_URI` 格式，检查用户名密码

### Q: 工作流创建失败
A: 查看日志确认节点数据格式是否正确

## 相关文档

- [FastGPT 官方文档](https://doc.fastgpt.cn)
- [FastAPI 文档](https://fastapi.tiangolo.com)
- [Chakra UI 文档](https://chakra-ui.com)
