# FastGPT 智能工作流生成系统设计文档

> **Generated:** 2026-02-22
> **Version:** 1.0

---

## 一、概述

本文档描述 FastGPT 智能工作流生成系统的完整设计方案。该系统基于 OpenCode Agent 架构，实现用户通过自然语言描述自动生成完整工作流的能力，包括动态插件开发、代码验证和持久化运行。

---

## 二、系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FastGPT Web UI                                  │
│  (对话式交互 + 工作流编辑器 + 可视化预览)                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP/WebSocket
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    FastGPT Backend (Next.js)                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  API Routes:                                                    │   │
│  │  - /api/core/workflow/ai/chat        (对话交互)                │   │
│  │  - /api/core/workflow/ai/plugin/*    (插件管理)                │   │
│  │  - /api/core/workflow/ai/workflow/*  (工作流管理)               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP/gRPC
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    OpenCode Agent Service (Python)                       │
│  • 智能对话引擎 (多轮对话 + 意图理解)                                  │
│  • 代码生成器 (Python/JavaScript)                                     │
│  • 工作流规划器 (节点编排 + 复杂度评估)                                │
│  • 插件构建器 (动态工具创建)                                          │
│  • 质量评估器 (自评 + 迭代优化)                                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
        ┌───────────────────┐           ┌───────────────────┐
        │  MinIO            │           │  OpenSandbox     │
        │  (代码存储)       │           │  (代码验证)       │
        └───────────────────┘           └───────────────────┘
```

### 2.2 技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| 主框架 | Next.js | 现有 FastGPT 框架 |
| 数据库 | MongoDB | 核心数据存储 |
| 文件存储 | MinIO | 代码/文件持久化 (S3 兼容) |
| 向量库 | Milvus | 知识库向量存储 (现有) |
| 缓存/队列 | Redis | 任务队列/缓存 (现有) |
| 代码执行 | FastGPT Sandbox + OpenSandbox | 插件验证 |
| AI Agent | OpenCode Agent | 智能对话+代码生成 |
| 容器化 | Docker | 插件服务部署 |

---

## 三、核心功能设计

### 3.1 交互模式

系统支持四种交互模式，根据用户需求复杂度自动选择：

#### 模式 A: 直接生成 (简单需求)

适用于用户需求明确、节点较少 (<10) 的场景。

```
用户: "帮我做一个简单的问答机器人"

AI 分析 → 生成工作流 → 自评 → 用户确认 → 保存
```

#### 模式 B: Plan-Execute (中等复杂度)

适用于需求涉及多个模块、需要在执行前确认的场景。

```
用户: "做一个客服机器人，能根据问题类型分流处理"

AI 分析 → 生成 Plan (分步骤说明) → 用户确认 → 执行 → 迭代优化
```

#### 模式 C: 深度研究 (复杂场景)

适用于需求涉及多个外部系统、需要进行调研的场景。

```
用户: "帮我做一个企业级智能客服，需要对接ERP系统查库存"

AI 研究计划 → 多轮搜索 → 分析 → 生成 → 自评 → 优化
```

#### 模式 D: 引导式问答 (信息不足)

适用于用户需求描述不清晰，需要补充信息的场景。

```
用户: "帮我做一个智能助手"

AI 询问关键信息 → 用户回答 → 补充信息 → ... → 收集完成 → 切换对应模式
```

### 3.2 动态节点获取

系统通过 FastGPT API 动态获取当前团队可用的节点：

```typescript
// API: POST /api/core/app/tool/getSystemToolTemplates
// Request: { teamId, isRoot, userTags? }

// Response:
{
  nodes: [
    { id: "chatNode", name: "AI对话", type: "builtin", installed: true },
    { id: "datasetSearchNode", name: "知识库搜索", type: "builtin", installed: true },
    { id: "httpToolSet", name: "HTTP工具", type: "custom", installed: true },
    { id: "mcpToolSet", name: "MCP工具", type: "custom", installed: false }
  ],
  plugins: [
    { id: "app_xxx", name: "我的客服机器人", type: "app" }
  ]
}
```

### 3.3 动态插件开发流程

当用户需求需要调用外部系统但平台没有对应工具时，系统自动创建新插件：

```
1. 分析需求 → 需要外部 API
2. 询问用户 → 提供 API 文档或信息
3. 分析文件 → 提取 API 定义
4. 生成代码 → 在 OpenSandbox 中生成插件代码
5. 代码验证 → 测试 API 调用
6. 代码存储 → 存入 MinIO
7. 服务部署 → Docker 容器化部署
8. 插件注册 → 注册到 FastGPT (httpToolSet)
9. 工作流引用 → 在工作流中使用新插件
```

### 3.4 文件上传处理

支持用户上传 Word/Excel/PDF 文件辅助描述需求：

| 文件类型 | 处理方式 | 提取内容 |
|---------|---------|---------|
| .docx | 文字提取 | 文本内容 |
| .xlsx | 表格解析 | 行列结构 + API 定义 |
| .pdf | OCR + 文字提取 | 文本内容 |
| .txt | 直接读取 | 文本内容 |

---

## 四、数据模型设计

### 4.1 MongoDB Schema 扩展

#### 4.1.1 AI 对话会话

```typescript
// Collection: aiWorkflowSession
{
  _id: ObjectId,
  teamId: string,
  tmbId: string,
  
  // 会话信息
  sessionId: string,
  mode: 'create' | 'optimize' | 'extend',
  status: 'active' | 'completed' | 'cancelled',
  
  // 对话历史
  messages: [{
    role: 'user' | 'assistant',
    content: string,
    attachments?: string[],
    timestamp: Date
  }],
  
  // 生成的工作流 (如果有)
  generatedWorkflowId?: string,
  
  createdAt: Date,
  updatedAt: Date
}
```

#### 4.1.2 插件源代码

```typescript
// Collection: pluginSourceCode
{
  _id: ObjectId,
  teamId: string,
  pluginId: string,           // 关联的 httpToolSet App ID
  
  // 存储位置
  minioPath: string,         // MinIO 路径
  
  // 代码信息
  language: 'python' | 'javascript',
  entryPoint: string,
  requirements?: string[],
  
  // 部署信息
  deploymentType: 'docker' | 'embedded',
  containerId?: string,
  endpoint?: string,
  
  // 版本管理
  version: string,
  versionHistory: [{
    version: string,
    createdAt: Date,
    commitMsg: string
  }],
  
  // 状态
  status: 'draft' | 'testing' | 'active' | 'error',
  
  createdAt: Date,
  updatedAt: Date
}
```

### 4.2 MinIO 存储结构

```
Bucket: fastgpt-plugins (私有桶)

/plugins/
├── {teamId}/
│   ├── {pluginId}/
│   │   ├── source/
│   │   │   ├── main.py
│   │   │   ├── requirements.txt
│   │   │   ├── config.json
│   │   │   └── tests/
│   │   │       └── test_main.py
│   │   ├── docker/
│   │   │   └── Dockerfile
│   │   └── metadata.json
│   └── workflows/
│       └── {workflowId}/
│           └── workflow.json
```

---

## 五、API 设计

### 5.1 对话交互 API

#### 5.1.1 发起对话

```
POST /api/core/workflow/ai/chat

Request:
{
  teamId: string,
  message: string,
  sessionId?: string,         // 继续已有会话
  attachments?: string[],    // 文件 ID 列表
  context?: {
    workflowId?: string,
    mode: 'create' | 'optimize' | 'extend'
  }
}

Response:
{
  sessionId: string,
  message: string,
  suggestions?: string[],
  workflowPreview?: {
    nodes: FlowNodeItemType[],
    edges: FlowEdgeItemType[]
  }
}
```

### 5.2 插件管理 API

#### 5.2.1 生成插件代码

```
POST /api/core/workflow/ai/plugin/generate

Request:
{
  teamId: string,
  name: string,
  description: string,
  apiSpec?: {
    url: string,
    method: string,
    headers?: object,
    bodySchema?: object
  },
  code?: string              // 可选，预设代码
}

Response:
{
  pluginId: string,
  code: string,
  status: 'generated'
}
```

#### 5.2.2 验证插件代码

```
POST /api/core/workflow/ai/plugin/verify

Request:
{
  teamId: string,
  pluginId: string,
  testInput?: object
}

Response:
{
  status: 'passed' | 'failed',
  output: any,
  errors?: string[]
}
```

#### 5.2.3 部署插件

```
POST /api/core/workflow/ai/plugin/deploy

Request:
{
  teamId: string,
  pluginId: string,
  deploymentType: 'docker' | 'embedded'
}

Response:
{
  pluginId: string,
  containerId?: string,
  endpoint: string,
  status: 'deploying' | 'running'
}
```

### 5.3 工作流管理 API

#### 5.3.1 创建工作流

```
POST /api/core/workflow/ai/workflow/create

Request:
{
  teamId: string,
  name: string,
  nodes: FlowNodeItemType[],
  edges: FlowEdgeItemType[],
  folderId?: string
}

Response:
{
  workflowId: string,
  nodes: FlowNodeItemType[],
  edges: FlowEdgeItemType[]
}
```

---

## 六、前端交互设计

### 6.1 对话界面

```
┌─────────────────────────────────────────────────────────────────────┐
│  🤖 AI 工作流助手                                      [新建] [历史] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  👤 用户                                                              │
│  我需要一个客服机器人，能回答产品问题并转接人工                         │
│                                                                     │
│  🤖 AI                                                               │
│  理解了你的需求。我先确认一下：                                       │
│                                                                     │
│  1. 知识库搜索：需要告诉我你的知识库名称                              │
│  2. 转接人工：需要配置转接目标 (企业微信/钉钉/其他)                   │
│                                                                     │
│  请确认以上理解是否正确？                                             │
│                                                                     │
│  [✓ 正确]  [补充信息]                                                │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  📎 添加附件                          ┌─────────────────────────┐   │
│  输入消息...                           [✨ 发送]                 │   │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 可视化预览

```
┌─────────────────────────────────────────────────────────────────────┐
│                    工作流预览                                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  复杂度: ★★★★☆ (5节点, 2分支)                                     │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  [开始] → [用户分类] → ┌── [技术问题] → AI回答               │ │
│  │                    │    ├── [其他问题] → 转接人工              │ │
│  │                    └── [知识库搜索] → AI回答                   │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  节点说明:                                                          │
│  • workflowStart - 接收用户输入                                      │
│  • classifyQuestion - 智能分类用户问题                               │
│  • datasetSearchNode - 搜索知识库                                   │
│  • chatNode - AI 生成回答                                           │
│  • userSelect - 转接人工                                            │
│                                                                     │
│  [上一步]  [返回修改]  [💾 保存]  [🔧 保存并编辑]                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 七、权限系统

### 7.1 权限模型

系统复用 FastGPT 现有权限模型：

| 概念 | 说明 |
|------|------|
| teamId | 团队唯一标识 |
| tmbId | 团队成员ID |
| isRoot | 超级管理员 |
| Permission | 资源权限 (Read/Write/Manage) |

### 7.2 权限检查

所有 AI 对话和操作均需要：

1. **团队权限验证**: 用户必须是团队成员
2. **资源权限验证**: 根据操作类型检查对应权限
3. **工作流权限**: 创建/编辑/删除需要不同权限级别

---

## 八、部署设计

### 8.1 Docker Compose 配置

```yaml
# docker-compose.yml 新增服务

services:
  # ... FastGPT 现有服务 ...
  
  # OpenCode Agent Service
  opencode-agent:
    image: fastgpt/opencode-agent:latest
    container_name: fastgpt-opencode-agent
    ports:
      - "8080:8080"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_BASE_URL=${OPENAI_BASE_URL}
      - MONGODB_URI=${MONGODB_URI}
      - MINIO_ENDPOINT=${MINIO_ENDPOINT}
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
      - REDIS_URL=${REDIS_URL}
    volumes:
      - ./opencode-data:/app/data
    networks:
      - fastgpt

  # OpenSandbox (可选)
  opensandbox:
    image: opensandbox/server:latest
    ports:
      - "7860:7860"
    networks:
      - fastgpt
```

---

## 九、质量保证

### 9.1 自评系统

生成的工作流自动进行质量评分：

| 维度 | 权重 | 评分项 |
|------|------|--------|
| 完整性 | 25% | 开始/结束节点、错误处理、兜底方案 |
| 逻辑性 | 25% | 节点顺序、条件分支、数据流 |
| 可用性 | 20% | 必填参数、引用有效、工具权限 |
| 效率 | 15% | 冗余节点、并行处理 |
| 用户体验 | 15% | 交互引导、错误提示 |

### 9.2 迭代优化

```
生成 → 自评 → 评分 < 70? → 自动重生成 → 自评 → ... → 用户确认
                         ↓
                   评分 ≥ 70 → 展示优化建议 → 用户选择
```

---

## 十、总结

本设计方案实现了以下核心能力：

1. ✅ **自然语言生成** - 用户描述需求，AI 自动生成工作流
2. ✅ **动态节点获取** - 实时获取团队可用节点
3. ✅ **智能插件开发** - 需要的工具不存在时自动创建
4. ✅ **代码验证与部署** - OpenSandbox 验证 + Docker 部署
5. ✅ **多种交互模式** - 直接生成/Plan/深度研究/引导式
6. ✅ **可视化预览** - 流程图展示，解决 JSON 不直观问题
7. ✅ **权限感知** - 所有操作在正确的团队空间中执行
8. ✅ **质量保证** - 自评迭代，确保生成质量
