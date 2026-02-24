# AI Workflow Generator 完整设计文档

## 1. 用户分层模型

### 1.1 三层用户画像

```
┌─────────────────────────────────────────────────────────┐
│                    用户分层模型                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Level 1: 探索者 (Explorer)                              │
│  ────────────────────────────────────                   │
│  特征: 不了解工作流概念，需要模板和引导                    │
│  行为: 浏览模板、尝试示例、学习概念                        │
│  需求: 可视化引导、预设模板、实时预览                      │
│                                                         │
│  Level 2: 构建者 (Builder)                              │
│  ────────────────────────────────────                   │
│  特征: 了解基本概念，能描述需求                            │
│  行为: 描述需求、调整参数、测试运行                        │
│  需求: 自然语言输入、智能建议、调试工具                    │
│                                                         │
│  Level 3: 专家 (Expert)                                 │
│  ────────────────────────────────────                   │
│  特征: 深入理解工作流，需要高级控制                        │
│  行为: 直接编辑节点、编写代码、管理版本                    │
│  需求: 代码编辑器、版本管理、团队协作                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 1.2 用户场景矩阵

| 场景 | 探索者 | 构建者 | 专家 |
|------|--------|--------|------|
| 首次使用 | 引导式教程 | 快速开始向导 | API 文档 |
| 创建工作流 | 选择模板 → 微调 | 描述需求 → AI 生成 | 手动编辑节点 |
| 调试问题 | 查看错误提示 | 查看日志 → 建议修复 | 直接修改配置 |
| 版本管理 | 不需要 | 简单回滚 | 完整 Git 集成 |
| 团队协作 | 不需要 | 分享链接 | 权限管理 |

---

## 2. 初学者引导系统设计

### 2.1 引导流程

```typescript
interface OnboardingFlow {
  // 1. 欢迎阶段
  welcome: {
    showTemplateGallery: boolean;  // 显示模板库
    quickStartOptions: string[];   // 快速开始选项
  };
  
  // 2. 学习阶段
  learning: {
    interactiveTutorial: boolean;  // 交互式教程
    conceptExplainer: boolean;     // 概念解释
    exampleWorkflows: string[];    // 示例工作流
  };
  
  // 3. 实践阶段
  practice: {
    guidedCreation: boolean;       // 引导式创建
    smartSuggestions: boolean;     // 智能建议
    realTimePreview: boolean;      // 实时预览
  };
}
```

### 2.2 模板系统

**模板分类：**

```
templates/
├── beginner/
│   ├── simple-chat/           # 简单对话
│   ├── qa-bot/                # 问答机器人
│   └── form-collector/        # 表单收集
├── intermediate/
│   ├── knowledge-qa/          # 知识库问答
│   ├── multi-round-chat/      # 多轮对话
│   └── data-processing/       # 数据处理
└── advanced/
    ├── agentic-workflow/      # Agent 工作流
    ├── custom-tools/          # 自定义工具
    └── integrations/          # 第三方集成
```

### 2.3 智能提示系统

```typescript
interface SmartHintSystem {
  // 输入提示
  inputHints: {
    autocomplete: string[];      // 自动补全
    examples: string[];          // 示例输入
    clarifyingQuestions: string[]; // 澄清问题
  };
  
  // 错误提示
  errorHints: {
    userFriendlyMessage: string; // 用户友好信息
    possibleCauses: string[];    // 可能原因
    suggestedFixes: string[];    // 建议修复
  };
  
  // 上下文提示
  contextHints: {
    nextStepSuggestion: string;  // 下一步建议
    relatedNodes: string[];      // 相关节点
    bestPractices: string[];     // 最佳实践
  };
}
```

---

## 3. 专家级功能设计

### 3.1 高级编辑器

```typescript
interface AdvancedEditor {
  // 代码编辑
  codeEditor: {
    language: 'typescript' | 'python' | 'json';
    syntaxHighlight: boolean;
    autoComplete: boolean;
    linting: boolean;
  };
  
  // 节点编辑
  nodeEditor: {
    customInputs: FieldConfig[];
    customOutputs: FieldConfig[];
    validationRules: ValidationRule[];
  };
  
  // 调试工具
  debugger: {
    breakpoints: boolean;
    stepExecution: boolean;
    variableInspector: boolean;
    callStack: boolean;
  };
}
```

### 3.2 版本管理系统

```typescript
interface VersionControl {
  // 版本操作
  operations: {
    createVersion: (workflowId: string, message: string) => Version;
    restoreVersion: (versionId: string) => Workflow;
    compareVersions: (v1: string, v2: string) => Diff;
    branchWorkflow: (workflowId: string, branchName: string) => Workflow;
  };
  
  // 版本历史
  history: {
    listVersions: (workflowId: string) => Version[];
    getVersion: (versionId: string) => Version;
    searchVersions: (query: string) => Version[];
  };
  
  // 协作功能
  collaboration: {
    shareWorkflow: (workflowId: string, userIds: string[]) => void;
    commentOnVersion: (versionId: string, comment: string) => void;
    requestReview: (versionId: string, reviewers: string[]) => void;
  };
}
```

### 3.3 高级节点配置

```typescript
interface AdvancedNodeConfig {
  // 变量映射
  variableMapping: {
    inputVariables: Map<string, VariableSource>;
    outputVariables: Map<string, VariableTarget>;
    transformFunctions: TransformFunction[];
  };
  
  // 条件分支
  conditionalBranching: {
    conditions: Condition[];
    branches: Branch[];
    defaultBranch: Branch;
  };
  
  // 错误处理
  errorHandling: {
    retryPolicy: RetryPolicy;
    fallbackBehavior: FallbackBehavior;
    errorOutputs: ErrorOutput[];
  };
}
```

---

## 4. LLM 集成方案

### 4.1 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                  LLM 集成架构                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  用户输入                                                │
│     │                                                   │
│     ▼                                                   │
│  ┌─────────────────┐                                    │
│  │ 意图分析器       │                                    │
│  │ IntentAnalyzer  │                                    │
│  └────────┬────────┘                                    │
│           │                                             │
│           ▼                                             │
│  ┌─────────────────┐                                    │
│  │ 上下文构建器     │                                    │
│  │ ContextBuilder  │                                    │
│  └────────┬────────┘                                    │
│           │                                             │
│           ▼                                             │
│  ┌─────────────────┐                                    │
│  │ Prompt 模板引擎  │                                    │
│  │ PromptEngine    │                                    │
│  └────────┬────────┘                                    │
│           │                                             │
│           ▼                                             │
│  ┌─────────────────┐                                    │
│  │ LLM 调用层       │                                    │
│  │ (支持多模型)     │                                    │
│  └────────┬────────┘                                    │
│           │                                             │
│           ▼                                             │
│  ┌─────────────────┐                                    │
│  │ 结果解析器       │                                    │
│  │ ResultParser    │                                    │
│  └─────────────────┘                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Prompt 工程

```typescript
// 系统提示模板
const SYSTEM_PROMPT = `
你是一个 FastGPT 工作流生成专家。你的任务是理解用户的自然语言描述，
并生成符合 FastGPT 规范的工作流配置。

## 可用节点类型
${AVAILABLE_NODES.map(n => `- ${n.type}: ${n.description}`).join('\n')}

## 输出规则
1. 必须包含 workflowStart 节点作为入口
2. 节点连接必须符合类型约束
3. 所有必需参数必须提供默认值
4. 返回 JSON 格式的工作流配置

## 用户等级适配
- 初学者: 使用简单节点，提供详细解释
- 构建者: 使用标准节点，提供配置建议
- 专家: 允许自定义节点，支持代码扩展
`;

// 用户提示模板
const USER_PROMPT_TEMPLATES = {
  create: `
用户需求: {{requirement}}
用户等级: {{userLevel}}
生成一个新的工作流配置。
  `,
  
  optimize: `
当前工作流: {{currentWorkflow}}
优化目标: {{optimizationGoal}}
分析并优化当前工作流。
  `,
  
  extend: `
当前工作流: {{currentWorkflow}}
扩展需求: {{extensionRequirement}}
在现有基础上扩展工作流功能。
  `
};
```

### 4.3 流式响应实现

```typescript
interface StreamingResponse {
  // SSE 流式输出
  streamToSSE: (response: AsyncIterable<LLMChunk>) => ReadableStream;
  
  // 增量更新 UI
  incrementalUpdate: (partial: PartialWorkflow) => void;
  
  // 错误恢复
  errorRecovery: {
    retryCount: number;
    fallbackModel: string;
    partialResultHandling: 'discard' | 'keep';
  };
}
```

---

## 5. 工作流验证系统

### 5.1 验证规则

```typescript
interface ValidationRule {
  id: string;
  name: string;
  level: 'error' | 'warning' | 'info';
  check: (workflow: Workflow) => ValidationResult;
}

// 核心验证规则
const VALIDATION_RULES: ValidationRule[] = [
  {
    id: 'entry-node-required',
    name: '入口节点必需',
    level: 'error',
    check: (workflow) => ({
      valid: workflow.nodes.some(n => n.isEntry),
      message: '工作流必须包含至少一个入口节点'
    })
  },
  {
    id: 'node-connection-valid',
    name: '节点连接有效性',
    level: 'error',
    check: (workflow) => {
      // 检查所有边的源和目标节点存在
      // 检查类型匹配
      // 检查循环依赖
    }
  },
  {
    id: 'required-inputs-provided',
    name: '必需输入已提供',
    level: 'error',
    check: (workflow) => {
      // 检查每个节点的必需输入是否有值或连接
    }
  },
  {
    id: 'performance-warning',
    name: '性能警告',
    level: 'warning',
    check: (workflow) => {
      // 检查可能导致性能问题的配置
      // 例如：过多的并发节点、大循环等
    }
  }
];
```

### 5.2 实时验证

```typescript
interface RealTimeValidator {
  // 节点级验证
  validateNode: (node: Node) => NodeValidationResult;
  
  // 边级验证
  validateEdge: (edge: Edge) => EdgeValidationResult;
  
  // 工作流级验证
  validateWorkflow: (workflow: Workflow) => WorkflowValidationResult;
  
  // 增量验证（只验证变更部分）
  incrementalValidate: (
    changes: WorkflowChange[],
    previousResult: ValidationResult
  ) => ValidationResult;
}
```

### 5.3 错误恢复建议

```typescript
interface ErrorRecoverySuggestion {
  errorType: string;
  userMessage: string;
  technicalDetails: string;
  suggestedFixes: {
    automatic: boolean;      // 是否可自动修复
    action: () => void;      // 修复动作
    description: string;     // 修复描述
  }[];
}
```

---

## 6. Session 管理集成

### 6.1 Session 数据模型

```typescript
interface AiWorkflowSession {
  _id: ObjectId;
  teamId: string;
  tmbId: string;
  sessionId: string;
  
  // 对话历史
  messages: {
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: Date;
    attachments?: string[];
    metadata?: Record<string, any>;
  }[];
  
  // 工作流状态
  workflowState: {
    currentWorkflow?: Workflow;
    previousVersions: {
      workflow: Workflow;
      timestamp: Date;
      trigger: 'user' | 'auto-save';
    }[];
    generatedNodes: string[];  // 已生成的节点 ID
    pendingChanges: boolean;
  };
  
  // 上下文信息
  context: {
    mode: 'create' | 'optimize' | 'extend';
    targetWorkflowId?: string;
    userPreferences: {
      preferredNodes: string[];
      avoidedPatterns: string[];
    };
    detectedIntent: {
      primary: string;
      secondary: string[];
      confidence: number;
    };
  };
  
  // 元数据
  metadata: {
    createdAt: Date;
    updatedAt: Date;
    status: 'active' | 'completed' | 'cancelled';
    generatedWorkflowId?: string;
  };
}
```

### 6.2 Session 生命周期

```
创建 ──────────────────────────────────────────────────────►
  │                                                        │
  │  ┌──────────┐   ┌──────────┐   ┌──────────┐          │
  │  │  active  │◄─►│  active  │◄─►│  active  │          │
  │  │ (轮次1)  │   │ (轮次2)  │   │ (轮次N)  │          │
  │  └──────────┘   └──────────┘   └──────────┘          │
  │       │              │              │                  │
  │       └──────────────┼──────────────┘                  │
  │                      │                                 │
  │                      ▼                                 │
  │              ┌───────────┐                             │
  │              │ completed │                             │
  │              │  /cancelled│                            │
  │              └───────────┘                             │
  │                                                        │
  └───────────────────────────────────────────────────────►
                        时间轴
```

### 6.3 上下文管理

```typescript
interface ContextManager {
  // 构建对话上下文
  buildContext: (sessionId: string) => ConversationContext;
  
  // 管理上下文窗口
  manageContextWindow: {
    maxTokens: number;
    strategy: 'sliding' | 'summarization' | 'hierarchical';
    priorityNodes: string[];  // 重要节点优先保留
  };
  
  // 跨 Session 记忆
  crossSessionMemory: {
    userPreferences: Record<string, any>;
    commonPatterns: Pattern[];
    learnedBehaviors: Behavior[];
  };
}
```

---

## 7. 实现优先级

### Phase 1: 基础闭环 (MVP)

1. **LLM 集成** - 接入真实 LLM API
2. **Session 管理** - 实现完整的会话持久化
3. **基础验证** - 实现核心验证规则
4. **错误提示** - 用户友好的错误信息

### Phase 2: 用户体验

1. **初学者引导** - 模板库 + 引导流程
2. **智能提示** - 输入建议 + 错误修复建议
3. **实时预览** - 工作流可视化预览

### Phase 3: 高级功能

1. **专家编辑器** - 代码编辑 + 高级配置
2. **版本管理** - 完整的版本控制系统
3. **团队协作** - 分享 + 评论 + 审核

---

## 8. 技术实现要点

### 8.1 关键文件修改

| 文件 | 修改内容 |
|------|----------|
| `projects/opencode-agent/src/agent/core.py` | 接入真实 LLM |
| `packages/service/core/workflow/ai/sessionController.ts` | 完善会话管理 |
| `packages/web/components/core/aiWorkflow/` | 新增引导和专家组件 |
| `packages/global/openapi/core/workflow/ai/` | 新增验证 API |

### 8.2 新增依赖

- LLM SDK (根据实际使用的模型)
- Schema 验证库 (zod 已有)
- Diff 工具 (版本对比)

---

## 9. 验收标准

### 9.1 功能验收

- [ ] 用户可以通过自然语言创建工作流
- [ ] 系统能正确识别用户意图
- [ ] 生成的工作流通过验证
- [ ] 初学者能完成引导教程
- [ ] 专家能使用高级功能

### 9.2 性能验收

- [ ] 对话响应时间 < 3s
- [ ] 工作流生成时间 < 10s
- [ ] 验证响应时间 < 500ms

### 9.3 质量验收

- [ ] 测试覆盖率 > 80%
- [ ] 无严重 bug
- [ ] 文档完整
