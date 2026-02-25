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
│  │   User Input → FastGPT API → Python Agent → vLLM → Workflow     │   │
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
│     vLLM       │  │  OpenSandbox  │  │    FastGPT     │
│  (LLM Brain)   │  │   (验证)       │  │    Sandbox     │
└────────────────┘  └────────────────┘  └────────────────┘
```

## 核心设计决策

| 方面 | 实现 |
|------|------|
| 大脑 | vLLM (本地部署的大模型服务) |
| 工作流生成 | LLM-based 生成 + 规则降级 |
| 用户交互 | 多轮交互确认 |
| 工作流生成 | 从 0 生成 + 优化现有 |
| 验证 | OpenSandbox 验证 |

## 技术栈

- **后端**: Python FastAPI, Node.js, TypeScript
- **前端**: React, Chakra UI, TypeScript
- **数据库**: MongoDB (PostgreSQL/pgvector)
- **LLM**: vLLM (本地部署)

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

# OpenCode API (可选，用于复杂工作流)
OPENCODE_API_URL=http://localhost:8080
OPENCODE_API_KEY=your-api-key

# vLLM 配置 (LLM 大脑)
VLLM_BASE_URL=http://localhost:38004
VLLM_MODEL=Qwen3-235B-A22B-Thinking-2507
VLLM_API_KEY=your-vllm-api-key

# FastGPT API
FASTGPT_API_URL=http://fastgpt:3000
FASTGPT_API_KEY=your-fastgpt-api-key
```

### 3. 启动 vLLM 服务

```bash
# 使用 Docker 启动 vLLM
docker run -d --name vllm \
  -p 38004:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  --env TF_ENABLE_ONEDNN_OPTS=0 \
  --gpu all \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen3-235B-A22B-Thinking-2507 \
  --tensor-parallel-size 8
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

返回完整的节点类型和工具信息:

```json
{
  "tools": [
    {
      "id": "tool_xxx",
      "pluginId": "plugin_xxx",
      "name": "天气查询",
      "description": "获取指定城市的天气信息",
      "flowNodeType": "tool",
      "installed": true,
      "inputs": [...],
      "outputs": [...],
      "tags": ["utility"],
      "version": "1.0.0"
    }
  ],
  "nodeTypes": [
    {
      "id": "workflowStart",
      "label": "开始",
      "category": "core",
      "description": "工作流入口节点"
    },
    {
      "id": "chatNode",
      "label": "AI 对话",
      "category": "ai",
      "description": "AI 对话节点，支持多种模型"
    }
  ],
  "categories": [
    {"id": "core", "label": "核心节点"},
    {"id": "ai", "label": "AI 节点"},
    {"id": "input", "label": "输入节点"}
  ]
}
```

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

## 数据流

```
1. 用户在前端输入自然语言描述
   ↓
2. FastGPT Backend (chat.ts)
   - 获取团队可用工具列表 (getSystemToolsWithInstalled)
   - 调用 /api/core/workflow/ai/nodes 获取完整工具/节点信息
   ↓
3. Python Agent (/api/ai-workflow/generate)
   - IntentAnalyzer: 分析用户意图和复杂度
   - WorkflowGenerator.generate(): 生成工作流
     ↓
     a) 构建 System Prompt (包含工具、节点、分类信息)
     b) 调用 vLLM API 生成工作流 JSON
     c) 解析 LLM 响应为节点和边
     d) 降级: 如果 LLM 失败，使用规则生成
   ↓
4. 返回工作流给前端
```

## 项目结构

```
projects/opencode-agent/
├── src/
│   ├── agent/
│   │   ├── core.py              # WorkflowAgent 核心逻辑
│   │   ├── intent_analyzer.py   # 意图分析 (复杂度分析 v2.0)
│   │   ├── workflow_generator.py # 工作流生成 (LLM + 规则降级)
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

projects/app/src/pages/api/core/workflow/ai/
├── chat.ts                     # AI 对话 API
├── nodes.ts                    # 获取可用节点 (扩展版)
└── workflow/
    ├── create.ts               # 创建工作流
    ├── confirm.ts              # 确认/回答
    └── validate.ts             # 验证工作流

packages/web/components/core/aiWorkflow/
├── AIWorkflowChat.tsx          # 对话界面组件
├── WorkflowPreview.tsx         # 工作流预览
├── api.ts                     # 前端 API 调用
└── index.ts                   # 导出
```

## vLLM 配置

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `VLLM_BASE_URL` | vLLM API 地址 | `http://fastgpt:3000` |
| `VLLM_MODEL` | 使用的模型名称 | `Qwen3-235B-A22B-Thinking-2507` |
| `VLLM_API_KEY` | API 密钥 | 空 |

### Docker Compose 配置

```yaml
services:
  ai-workflow-agent:
    image: opencode-agent:latest
    ports:
      - "8080:8080"
    environment:
      - FASTGPT_API_URL=http://fastgpt:3000
      - FASTGPT_API_KEY=${FASTGPT_API_KEY}
      - VLLM_BASE_URL=http://host.docker.internal:38004
      - VLLM_MODEL=Qwen3-235B-A22B-Thinking-2507
      - VLLM_API_KEY=${VLLM_API_KEY}
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

### 支持的模型

推荐使用支持 Function Calling 的模型:
- Qwen3-235B-A22B-Thinking-2507
- Qwen2.5-72B-Instruct
- Llama 3.1 70B

## 开发指南

### 添加新的 AI 能力

1. 修改 `projects/opencode-agent/src/agent/workflow_generator.py`
2. 在 `WorkflowGenerator` 类中添加新方法
3. 更新 API Schema (`packages/global/openapi/core/workflow/ai/api.d.ts`)
4. 更新前端 API 调用 (`packages/web/components/core/aiWorkflow/api.ts`)

### 添加新的节点类型

1. 在 FastGPT 核心中添加节点定义 (`FlowNodeTypeEnum`)
2. 更新 `nodes.ts` API 返回新节点元数据
3. 更新 `workflow_generator.py` 中的节点元数据

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
  ai-workflow-agent:
    image: opencode-agent:latest
    ports:
      - "8080:8080"
    environment:
      - FASTGPT_API_URL=http://fastgpt:3000
      - VLLM_BASE_URL=http://vllm:38004
      - VLLM_MODEL=Qwen3-235B-A22B-Thinking-2507

  vllm:
    image: vllm/vllm-openai:latest
    ports:
      - "38004:8000"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

## 工作流生成模式

| 模式 | 说明 | Context 参数 |
|------|------|-------------|
| **从 0 生成** | 用户描述需求 → Agent 生成完整工作流 | `mode: "create"` |
| **优化现有** | 用户选择现有工作流 + 修改意图 → Agent 生成修改后的工作流 | `mode: "optimize"`, `workflowId: "xxx"` |

## 高级模式特性

1. **LLM 生成**：使用 vLLM 进行智能工作流生成
2. **自动降级**：LLM 失败时使用规则生成
3. **多轮交互**：支持用户确认和问答
4. **预览编辑**：生成后可预览、修改后再发布

## 常见问题

### Q: vLLM 无法连接
A: 检查 `VLLM_BASE_URL` 环境变量，确保 vLLM 服务正常运行

### Q: 工作流生成失败
A: 查看日志确认 vLLM 调用是否正常，检查模型是否支持 JSON 输出

### Q: 多轮交互如何工作？
A: 当 Agent 返回 `status: "need_more_info"` 和 `questions` 时，前端显示问题，用户回答后调用 `/confirm` API

### Q: 如何切换到其他 LLM 提供商？
A: 修改 `workflow_generator.py` 中的 `_call_llm()` 方法，支持 OpenAI、Anthropic 等 API

---

## 当前实现状态 (2026-02-24)

### 已完成

| 组件 | 状态 | 文件 |
|------|------|------|
| Python Agent | ✅ 完成 | `projects/opencode-agent/` |
| FastGPT Backend API | ✅ 完成 | `projects/app/src/pages/api/core/workflow/ai/` |
| 前端组件 | ✅ 完成 | `packages/web/components/core/aiWorkflow/` |
| vLLM 集成 | ✅ 完成 | `workflow_generator.py` |
| 扩展节点 API | ✅ 完成 | `/api/core/workflow/ai/nodes` |
| 工作流验证 | ✅ 完成 | `/workflow/validate` |
| 类型定义 | ✅ 完成 | `packages/global/openapi/core/workflow/ai/api.d.ts` |

### 环境变量

```bash
# vLLM 配置 (必须)
VLLM_BASE_URL=http://localhost:38004
VLLM_MODEL=Qwen3-235B-A22B-Thinking-2507
VLLM_API_KEY=your-vllm-api-key

# FastGPT 配置
FASTGPT_API_URL=http://fastgpt:3000
FASTGPT_API_KEY=your-fastgpt-api-key
```

## 相关文档

- [FastGPT 官方文档](https://doc.fastgpt.cn)
- [vLLM 官方文档](https://docs.vllm.ai)
- [Qwen 模型](https://qwen.readthedocs.io/)
- [FastGPT 官方文档](https://doc.fastgpt.cn)
- [vLLM 官方文档](https://docs.vllm.ai)
- [Qwen 模型](https://qwen.readthedocs.io/)

---

# 更新日志 (2026-02-25)

## 新增功能

### 1. 流式生成 (Streaming Generation)
- 支持 SSE 流式输出，实时展示工作流生成进度
- 端点: `POST /api/ai-workflow/generate/stream`

### 2. 熔断器 (Circuit Breaker)
- 自动修复验证失败的工作流，最多 3 次尝试
- 超过次数后触发人工审核

### 3. 工作流模板 (Workflow Templates)
- 保存和加载工作流模板
- 支持标签搜索和名称搜索
- SQLite 持久化存储
- 端点: `POST/GET/DELETE /api/ai-workflow/templates/*`

### 4. 增强验证 (Enhanced Validation)
- 循环依赖检测
- 节点命名规范检查
- 必需配置验证
- 性能警告

### 5. 工作流导出/导入
- 支持 JSON 和 YAML 格式
- 端点: `/api/ai-workflow/export`, `/api/ai-workflow/import`

### 6. 模拟数据生成 & 预览
- 端点: `/api/ai-workflow/mock-data`, `/api/ai-workflow/preview`

### 7. 国际化
- 支持 zh-CN, en, zh-Hant

### 8. 安全特性
- API 密钥认证
- 请求频率限制
- 输入净化
- 结构化日志

## API 完整端点列表

| 方法 | 端点 | 认证 |
|------|------|------|
| POST | `/api/ai-workflow/generate` | ✅ |
| POST | `/api/ai-workflow/generate/stream` | ✅ |
| POST | `/api/ai-workflow/validate` | ✅ |
| POST | `/api/ai-workflow/export` | ✅ |
| POST | `/api/ai-workflow/import` | ✅ |
| POST | `/api/ai-workflow/templates/save` | ✅ |
| GET | `/api/ai-workflow/templates` | ✅ |
| DELETE | `/api/ai-workflow/templates/{id}` | ✅ |
| POST | `/api/ai-workflow/mock-data` | ✅ |
| POST | `/api/ai-workflow/preview` | ✅ |
| GET | `/health` | ❌ |

## 环境变量

```bash
# API 认证
OPENCODE_API_KEYS=key1,key2

# 频率限制
RATE_LIMIT_MAX=100
RATE_LIMIT_WINDOW=60

# 数据库
OPENCODE_DB_PATH=/tmp/opencode_agent.db
```

## 使用示例

```bash
# 认证请求
curl -X POST http://localhost:8080/api/ai-workflow/generate \
  -H "X-API-Key: your-api-key" \
  -d '{"userIntent": "创建工作流"}'

# 导出 JSON
curl -X POST http://localhost:8080/api/ai-workflow/export \
  -H "X-API-Key: your-api-key" \
  -d '{"workflow": {...}, "format": "json"}'
```
