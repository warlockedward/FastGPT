# AI Workflow Generator Phase 1 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现 MVP 版本 - 完整的 LLM 集成、Session 管理、基础验证和错误提示

**Architecture:** 
- Python FastAPI 服务作为 AI 引擎，处理 LLM 调用和意图分析
- Next.js API 层作为网关，处理认证和请求转发
- MongoDB 存储 Session 和 Plugin 数据

**Tech Stack:** Python 3.10+, FastAPI, OpenAI/Claude SDK, TypeScript, Next.js, MongoDB

---

## Task 1: LLM 集成 - Python Agent

### 1.1 修改 FastGPT API Client

**Files:**
- Modify: `projects/opencode-agent/src/tools/fastgpt.py`

**Step 1: 编写失败的测试**

```python
# projects/opencode-agent/tests/test_llm_client.py
import pytest
from unittest.mock import AsyncMock, patch

async def test_get_available_nodes_returns_list():
    """测试获取可用节点列表"""
    # TODO: 实现测试
    pass
```

**Step 2: 实现 LLM Client**

```python
# projects/opencode-agent/src/tools/fastgpt.py
import httpx
from typing import Optional, Any
import os

class FastGPTClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0
        )
    
    async def get_available_nodes(self, team_id: str) -> dict:
        response = await self.client.post(
            f"{self.base_url}/api/core/app/tool/getSystemToolTemplates",
            json={"teamId": team_id}
        )
        return response.json()
```

**Step 3: 提交代码**

```bash
git add projects/opencode-agent/src/tools/fastgpt.py
git commit -m "feat: add FastGPT API client for nodes"
```

---

### 1.2 集成 LLM (Intent Analysis)

**Files:**
- Modify: `projects/opencode-agent/src/agent/core.py`

**Step 1: 编写失败的测试**

```python
# tests/test_intent_analyzer.py
import pytest
from unittest.mock import AsyncMock, MagicMock

async def test_analyze_intent_returns_structured_result():
    """测试意图分析返回结构化结果"""
    from src.agent.intent_analyzer import IntentAnalyzer
    
    analyzer = IntentAnalyzer(api_key="test-key")
    result = await analyzer.analyze("创建一个简单的工作流")
    
    assert result["intent"] in ["create", "optimize", "extend", "unknown"]
    assert "confidence" in result
    assert "entities" in result
```

**Step 2: 运行测试验证失败**

```
Expected: FAIL - IntentAnalyzer not found
```

**Step 3: 实现 IntentAnalyzer**

```python
# projects/opencode-agent/src/agent/intent_analyzer.py
from typing import Dict, Any, List
import json

class IntentAnalyzer:
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
        
    SYSTEM_PROMPT = """你是一个工作流意图分析专家。
分析用户的自然语言输入，识别以下意图：
- create: 创建新工作流
- optimize: 优化现有工作流
- extend: 扩展现有工作流
- unknown: 无法理解的输入

返回 JSON 格式:
{
  "intent": "create|optimize|extend|unknown",
  "confidence": 0.0-1.0,
  "entities": {"node_types": [], "requirements": []},
  "suggestions": []
}"""
    
    async def analyze(self, message: str) -> Dict[str, Any]:
        # 调用 LLM 进行意图分析
        # TODO: 实现 LLM 调用
        pass
```

**Step 4: 运行测试验证通过**

```
Expected: PASS
```

**Step 5: 提交代码**

```bash
git add projects/opencode-agent/src/agent/
git commit -m "feat: add intent analyzer with LLM"
```

---

### 1.3 实现 Workflow Generator

**Files:**
- Modify: `projects/opencode-agent/src/agent/core.py`

**Step 1: 编写测试**

```python
async def test_generate_workflow_creates_valid_structure():
    """测试生成工作流返回有效结构"""
    from src.agent.workflow_generator import WorkflowGenerator
    
    generator = WorkflowGenerator(fastgpt_client=mock_client)
    result = await generator.generate(
        requirement="创建一个简单对话工作流",
        available_nodes=[{"type": "chatNode", "name": "AI 对话"}]
    )
    
    assert "nodes" in result
    assert "edges" in result
    assert any(n["type"] == "workflowStart" for n in result["nodes"])
```

**Step 2: 实现 WorkflowGenerator**

```python
# projects/opencode-agent/src/agent/workflow_generator.py
from typing import Dict, Any, List

class WorkflowGenerator:
    def __init__(self, fastgpt_client, llm_client):
        self.client = fastgpt_client
        self.llm = llm_client
    
    async def generate(self, requirement: str, available_nodes: List[Dict]) -> Dict[str, Any]:
        # 1. 调用 LLM 生成工作流配置
        # 2. 解析返回的 JSON
        # 3. 验证节点连接
        # 4. 返回标准化格式
        pass
```

---

## Task 2: Session 管理集成

### 2.1 完善 Session Schema

**Files:**
- Modify: `packages/service/core/workflow/ai/sessionSchema.ts`

**Step 1: 验证现有 Schema**

```typescript
// 检查现有字段是否完整
// 当前已定义: teamId, tmbId, sessionId, mode, status, messages, generatedWorkflowId
// 需要添加: workflowState, context
```

**Step 2: 更新 Schema**

```typescript
// packages/service/core/workflow/ai/sessionSchema.ts
import { connectionMongo, getMongoModel } from '../../../common/mongo';
const { Schema } = connectionMongo;

const ChatMessageSchema = new Schema({
  role: {
    type: String,
    enum: ['user', 'assistant', 'system'],
    required: true
  },
  content: {
    type: String,
    required: true
  },
  attachments: {
    type: [String],
    default: []
  },
  timestamp: {
    type: Date,
    default: () => new Date()
  }
});

const WorkflowStateSchema = new Schema({
  currentWorkflow: {
    type: Object,
    default: null
  },
  previousVersions: [{
    workflow: Object,
    timestamp: Date,
    trigger: {
      type: String,
      enum: ['user', 'auto-save'],
      default: 'user'
    }
  }],
  generatedNodes: [{
    type: String
  }],
  pendingChanges: {
    type: Boolean,
    default: false
  }
});

const AiWorkflowSessionSchema = new Schema({
  teamId: {
    type: String,
    required: true
  },
  tmbId: {
    type: String,
    required: true
  },
  sessionId: {
    type: String,
    required: true,
    index: true
  },
  mode: {
    type: String,
    enum: ['create', 'optimize', 'extend'],
    default: 'create'
  },
  status: {
    type: String,
    enum: ['active', 'completed', 'cancelled'],
    default: 'active'
  },
  messages: {
    type: [ChatMessageSchema],
    default: []
  },
  workflowState: {
    type: WorkflowStateSchema,
    default: () => ({})
  },
  context: {
    mode: {
      type: String,
      enum: ['create', 'optimize', 'extend'],
      default: 'create'
    },
    targetWorkflowId: String,
    userPreferences: {
      preferredNodes: [String],
      avoidedPatterns: [String]
    },
    detectedIntent: {
      primary: String,
      secondary: [String],
      confidence: Number
    }
  },
  generatedWorkflowId: {
    type: String
  },
  createdAt: {
    type: Date,
    default: () => new Date()
  },
  updatedAt: {
    type: Date,
    default: () => new Date()
  }
});

export const MongoAiWorkflowSession = getMongoModel(
  'aiWorkflowSession',
  AiWorkflowSessionSchema
);
```

**Step 3: 提交代码**

```bash
git add packages/service/core/workflow/ai/sessionSchema.ts
git commit -m "feat: add workflow state and context to session schema"
```

---

### 2.2 完善 Session Controller

**Files:**
- Modify: `packages/service/core/workflow/ai/sessionController.ts`

**Step 1: 编写测试**

```typescript
// test/cases/service/workflow/ai/sessionController.test.ts
import { describe, it, expect, beforeEach } from 'vitest';

describe('SessionController', () => {
  it('should create session with context', async () => {
    const session = await createSession({
      teamId: 'team-123',
      tmbId: 'tmb-123',
      mode: 'create',
      context: {
        mode: 'create',
        detectedIntent: {
          primary: 'create',
          secondary: [],
          confidence: 0.9
        }
      }
    });
    
    expect(session.sessionId).toBeDefined();
    expect(session.context.mode).toBe('create');
  });
  
  it('should add message to session', async () => {
    const session = await addMessage('session-123', {
      role: 'user',
      content: '创建一个工作流'
    });
    
    expect(session.messages.length).toBe(1);
    expect(session.messages[0].role).toBe('user');
  });
});
```

**Step 2: 实现 Controller**

```typescript
// packages/service/core/workflow/ai/sessionController.ts
import { MongoAiWorkflowSession } from './sessionSchema';
import { getNanoid } from '@fastgpt/global/common/string/tools';

export const createSession = async (data: {
  teamId: string;
  tmbId: string;
  mode?: 'create' | 'optimize' | 'extend';
  context?: {
    mode: 'create' | 'optimize' | 'extend';
    targetWorkflowId?: string;
    userPreferences?: {
      preferredNodes?: string[];
      avoidedPatterns?: string[];
    };
    detectedIntent?: {
      primary: string;
      secondary?: string[];
      confidence?: number;
    };
  };
}) => {
  const session = await MongoAiWorkflowSession.create({
    teamId: data.teamId,
    tmbId: data.tmbId,
    sessionId: getNanoid(),
    mode: data.mode || 'create',
    status: 'active',
    messages: [],
    workflowState: {
      currentWorkflow: null,
      previousVersions: [],
      generatedNodes: [],
      pendingChanges: false
    },
    context: data.context || {
      mode: data.mode || 'create'
    }
  });
  return session;
};

export const addMessage = async (
  sessionId: string,
  message: {
    role: 'user' | 'assistant' | 'system';
    content: string;
    attachments?: string[];
  }
) => {
  const session = await MongoAiWorkflowSession.findOneAndUpdate(
    { sessionId },
    {
      $push: { 
        messages: { ...message, timestamp: new Date() } 
      },
      $set: { updatedAt: new Date() }
    },
    { new: true }
  );
  return session;
};

export const getSession = async (sessionId: string) => {
  return MongoAiWorkflowSession.findOne({ sessionId });
};

export const updateSessionStatus = async (
  sessionId: string,
  status: 'active' | 'completed' | 'cancelled'
) => {
  return MongoAiWorkflowSession.findOneAndUpdate(
    { sessionId },
    { $set: { status, updatedAt: new Date() } },
    { new: true }
  );
};

export const updateWorkflowState = async (
  sessionId: string,
  workflowState: {
    currentWorkflow?: any;
    generatedNodes?: string[];
    pendingChanges?: boolean;
  }
) => {
  return MongoAiWorkflowSession.findOneAndUpdate(
    { sessionId },
    { 
      $set: { 
        'workflowState.currentWorkflow': workflowState.currentWorkflow,
        'workflowState.generatedNodes': workflowState.generatedNodes,
        'workflowState.pendingChanges': workflowState.pendingChanges,
        updatedAt: new Date()
      }
    },
    { new: true }
  );
};

export const saveWorkflowVersion = async (
  sessionId: string,
  workflow: any,
  trigger: 'user' | 'auto-save' = 'user'
) => {
  return MongoAiWorkflowSession.findOneAndUpdate(
    { sessionId },
    {
      $push: {
        'workflowState.previousVersions': {
          workflow,
          timestamp: new Date(),
          trigger
        }
      },
      $set: { updatedAt: new Date() }
    },
    { new: true }
  );
};
```

**Step 3: 提交代码**

```bash
git add packages/service/core/workflow/ai/sessionController.ts
git commit -m "feat: add workflow state management to session controller"
```

---

## Task 3: 工作流验证系统

### 3.1 创建验证服务

**Files:**
- Create: `packages/service/core/workflow/ai/validator.ts`

**Step 1: 编写测试**

```typescript
// test/cases/service/workflow/ai/validator.test.ts
import { describe, it, expect } from 'vitest';
import { validateWorkflow } from '@fastgpt/service/core/workflow/ai/validator';

describe('WorkflowValidator', () => {
  it('should fail when no entry node', async () => {
    const workflow = {
      nodes: [{ id: 'chat', type: 'chatNode' }],
      edges: []
    };
    
    const result = await validateWorkflow(workflow);
    expect(result.valid).toBe(false);
    expect(result.errors.some(e => e.id === 'entry-node-required')).toBe(true);
  });
  
  it('should pass valid workflow', async () => {
    const workflow = {
      nodes: [
        { id: 'start', type: 'workflowStart', isEntry: true },
        { id: 'chat', type: 'chatNode' }
      ],
      edges: [
        { source: 'start', target: 'chat' }
      ]
    };
    
    const result = await validateWorkflow(workflow);
    expect(result.valid).toBe(true);
    expect(result.errors.length).toBe(0);
  });
});
```

**Step 2: 实现 Validator**

```typescript
// packages/service/core/workflow/ai/validator.ts
export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface ValidationError {
  id: string;
  message: string;
  nodeIds?: string[];
}

export interface ValidationWarning {
  id: string;
  message: string;
  nodeIds?: string[];
}

// 核心验证规则
const VALIDATION_RULES = [
  {
    id: 'entry-node-required',
    name: '入口节点必需',
    level: 'error' as const,
    check: (workflow: any): ValidationError | null => {
      const hasEntry = workflow.nodes?.some((n: any) => n.isEntry || n.type === 'workflowStart');
      if (!hasEntry) {
        return {
          id: 'entry-node-required',
          message: '工作流必须包含至少一个入口节点 (workflowStart)'
        };
      }
      return null;
    }
  },
  {
    id: 'node-connection-valid',
    name: '节点连接有效性',
    level: 'error' as const,
    check: (workflow: any): ValidationError | null => {
      const nodeIds = new Set(workflow.nodes?.map((n: any) => n.id) || []);
      
      for (const edge of workflow.edges || []) {
        if (!nodeIds.has(edge.source)) {
          return {
            id: 'node-connection-valid',
            message: `边引用的源节点不存在: ${edge.source}`,
            nodeIds: [edge.source]
          };
        }
        if (!nodeIds.has(edge.target)) {
          return {
            id: 'node-connection-valid',
            message: `边引用的目标节点不存在: ${edge.target}`,
            nodeIds: [edge.target]
          };
        }
      }
      return null;
    }
  },
  {
    id: 'no-circular-dependency',
    name: '无循环依赖',
    level: 'error' as const,
    check: (workflow: any): ValidationError | null => {
      // 使用 DFS 检测循环
      const adj = new Map<string, string[]>();
      for (const edge of workflow.edges || []) {
        if (!adj.has(edge.source)) adj.set(edge.source, []);
        adj.get(edge.source)!.push(edge.target);
      }
      
      const visited = new Set<string>();
      const recursionStack = new Set<string>();
      
      const hasCycle = (node: string): boolean => {
        visited.add(node);
        recursionStack.add(node);
        
        for (const next of adj.get(node) || []) {
          if (!visited.has(next)) {
            if (hasCycle(next)) return true;
          } else if (recursionStack.has(next)) {
            return true;
          }
        }
        
        recursionStack.delete(node);
        return false;
      };
      
      for (const node of workflow.nodes || []) {
        if (!visited.has(node.id)) {
          if (hasCycle(node.id)) {
            return {
              id: 'no-circular-dependency',
              message: '工作流存在循环依赖'
            };
          }
        }
      }
      return null;
    }
  }
];

export async function validateWorkflow(workflow: any): Promise<ValidationResult> {
  const errors: ValidationError[] = [];
  const warnings: ValidationWarning[] = [];
  
  for (const rule of VALIDATION_RULES) {
    if (rule.level === 'error') {
      const error = rule.check(workflow);
      if (error) errors.push(error);
    } else {
      const warning = rule.check(workflow);
      if (warning) warnings.push(warning as ValidationWarning);
    }
  }
  
  return {
    valid: errors.length === 0,
    errors,
    warnings
  };
}

export async function validateNode(node: any): Promise<ValidationResult> {
  // 节点级验证
  const errors: ValidationError[] = [];
  
  if (!node.id) {
    errors.push({ id: 'node-id-required', message: '节点必须有 ID' });
  }
  
  if (!node.type) {
    errors.push({ id: 'node-type-required', message: '节点必须有类型' });
  }
  
  return {
    valid: errors.length === 0,
    errors,
    warnings: []
  };
}
```

**Step 3: 提交代码**

```bash
git add packages/service/core/workflow/ai/validator.ts
git commit -m "feat: add workflow validation system"
```

---

## Task 4: 错误提示系统

### 4.1 创建错误提示服务

**Files:**
- Create: `packages/service/core/workflow/ai/errorHandler.ts`

**Step 1: 编写测试**

```typescript
// test/cases/service/workflow/ai/errorHandler.test.ts
import { describe, it, expect } from 'vitest';
import { getErrorSuggestion } from '@fastgpt/service/core/workflow/ai/errorHandler';

describe('ErrorHandler', () => {
  it('should return suggestion for entry node error', async () => {
    const suggestion = getErrorSuggestion({
      errorType: 'entry-node-required',
      userLevel: 'beginner'
    });
    
    expect(suggestion.userMessage).toBeDefined();
    expect(suggestion.suggestedFixes.length).toBeGreaterThan(0);
  });
});
```

**Step 2: 实现 ErrorHandler**

```typescript
// packages/service/core/workflow/ai/errorHandler.ts

export interface ErrorSuggestion {
  userMessage: string;
  technicalDetails: string;
  possibleCauses: string[];
  suggestedFixes: {
    automatic: boolean;
    action: () => void;
    description: string;
    code?: string;
  }[];
}

const ERROR_SUGGESTIONS: Record<string, (userLevel: string) => ErrorSuggestion> = {
  'entry-node-required': (userLevel) => ({
    userMessage: '你的工作流缺少一个开始节点',
    technicalDetails: '工作流必须包含 workflowStart 节点作为入口',
    possibleCauses: [
      '没有添加开始节点',
      '开始节点被删除了',
      '忘记设置入口标记'
    ],
    suggestedFixes: [
      {
        automatic: true,
        action: () => ({ type: 'ADD_NODE', nodeType: 'workflowStart' }),
        description: '自动添加开始节点',
        code: `{ "type": "workflowStart", "id": "start" }`
      }
    ]
  }),
  
  'node-connection-valid': (userLevel) => ({
    userMessage: '有些节点连接是无效的',
    technicalDetails: '边引用的源或目标节点不存在',
    possibleCauses: [
      '删除了连接的节点',
      '节点 ID 拼写错误',
      '复制粘贴时没有更新 ID'
    ],
    suggestedFixes: [
      {
        automatic: false,
        action: () => ({ type: 'MANUAL_FIX' }),
        description: '检查并修正节点 ID'
      }
    ]
  }),
  
  'no-circular-dependency': (userLevel) => ({
    userMessage: '工作流中存在循环',
    technicalDetails: '节点之间形成了循环依赖',
    possibleCauses: [
      '条件分支形成了闭环',
      '循环节点配置错误'
    ],
    suggestedFixes: [
      {
        automatic: false,
        action: () => ({ type: 'REVIEW_EDGES' }),
        description: '检查所有边的连接'
      }
    ]
  }),
  
  'llm-connection-failed': (userLevel) => ({
    userMessage: userLevel === 'beginner' 
      ? 'AI 服务暂时不可用，请稍后重试'
      : 'LLM API 连接失败，请检查网络和 API Key 配置',
    technicalDetails: '无法连接到 LLM 服务',
    possibleCauses: [
      'API Key 过期或无效',
      '网络问题',
      '服务提供商故障'
    ],
    suggestedFixes: [
      {
        automatic: false,
        action: () => ({ type: 'CHECK_CONFIG' }),
        description: '检查 OPENAI_API_KEY 环境变量'
      }
    ]
  }),
  
  'session-not-found': (userLevel) => ({
    userMessage: '会话已过期，请重新开始',
    technicalDetails: '指定的 sessionId 不存在或已过期',
    possibleCauses: [
      '会话超时',
      '会话被删除',
      'sessionId 错误'
    ],
    suggestedFixes: [
      {
        automatic: true,
        action: () => ({ type: 'CREATE_NEW_SESSION' }),
        description: '创建新的会话'
      }
    ]
  })
};

export function getErrorSuggestion(
  error: { errorType: string; details?: string },
  options?: { userLevel?: string }
): ErrorSuggestion {
  const userLevel = options?.userLevel || 'intermediate';
  const template = ERROR_SUGGESTIONS[error.errorType];
  
  if (!template) {
    return {
      userMessage: '发生了一个错误',
      technicalDetails: error.details || '未知错误',
      possibleCauses: ['请稍后重试'],
      suggestedFixes: [
        {
          automatic: false,
          action: () => ({ type: 'RETRY' }),
          description: '重试操作'
        }
      ]
    };
  }
  
  return template(userLevel);
}

export function formatUserError(error: ErrorSuggestion): string {
  let message = `❌ ${error.userMessage}\n\n`;
  
  if (error.suggestedFixes.length > 0) {
    message += '💡 可以尝试以下方法：\n';
    error.suggestedFixes.forEach((fix, index) => {
      message += `${index + 1}. ${fix.description}\n`;
    });
  }
  
  return message;
}
```

**Step 3: 提交代码**

```bash
git add packages/service/core/workflow/ai/errorHandler.ts
git commit -m "feat: add error handling and user-friendly suggestions"
```

---

## Task 5: 集成测试

### 5.1 端到端测试

**Files:**
- Create: `test/integration/aiWorkflow.e2e.test.ts`

```typescript
import { describe, it, expect, beforeAll } from 'vitest';

describe('AI Workflow E2E', () => {
  const baseUrl = process.env.API_BASE_URL || 'http://localhost:3000';
  
  it('should complete full workflow creation flow', async () => {
    // 1. 创建会话
    const createSessionRes = await fetch(`${baseUrl}/api/core/workflow/ai/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ teamId: 'test-team' })
    });
    expect(createSessionRes.ok).toBe(true);
    const { sessionId } = await createSessionRes.json();
    
    // 2. 发送消息
    const chatRes = await fetch(`${baseUrl}/api/core/workflow/ai/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        teamId: 'test-team',
        sessionId,
        message: '创建一个简单的工作流'
      })
    });
    expect(chatRes.ok).toBe(true);
    const chatResult = await chatRes.json();
    
    // 3. 验证返回的工作流
    expect(chatResult.workflowPreview).toBeDefined();
    
    // 4. 创建工作流
    const createWorkflowRes = await fetch(`${baseUrl}/api/core/workflow/ai/workflow/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        teamId: 'test-team',
        name: 'Test Workflow',
        nodes: chatResult.workflowPreview.nodes,
        edges: chatResult.workflowPreview.edges
      })
    });
    expect(createWorkflowRes.ok).toBe(true);
    const workflowResult = await createWorkflowRes.json();
    
    expect(workflowResult.workflowId).toBeDefined();
  });
});
```

---

## 总结

### 实现顺序

1. **Task 1**: LLM 集成 (最核心)
   - FastGPT Client
   - Intent Analyzer
   - Workflow Generator

2. **Task 2**: Session 管理 (数据持久化)
   - 完善 Schema
   - 完善 Controller

3. **Task 3**: 验证系统 (质量保障)
   - Validator 实现
   - 集成到 Generator

4. **Task 4**: 错误处理 (用户体验)
   - Error Handler
   - 用户友好的提示

5. **Task 5**: 端到端测试
   - 完整流程测试

### 预期结果

完成 Phase 1 后：
- ✅ 用户可以通过自然语言创建工作流
- ✅ 系统能正确识别意图
- ✅ 生成的工作流通过验证
- ✅ 错误信息友好易懂
- ✅ Session 状态持久化
