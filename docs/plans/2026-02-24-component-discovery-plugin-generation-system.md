# FastGPT 工作流组件自动发现与自定义插件生成系统

## 1. 问题背景与目标

### 1.1 用户需求
OpenCode-Agent 需要实现以下能力：
1. **实时获取 FastGPT 组件**: 获取所有可用的工作流节点、插件和工具
2. **自动化构建 Workflow**: 在自动化构建时正确使用这些组件
3. **自定义插件生成**: 当所需组件不存在时：
   - 生成后端代码
   - 在 FastGPT 中创建插件实例
   - 在 Workflow 中调用生成的插件

### 1.2 核心挑战
- FastGPT 有 **40+ 种工作流节点类型**
- 插件系统需要通过 API 注册
- 插件开发涉及后端代码生成和前端配置
- 需要实现代码生成 → 插件创建 → 工作流集成的完整链路

---

## 2. FastGPT 现有组件分析

### 2.1 工作流节点类型 (FlowNodeTypeEnum)

| 节点类型 | 用途 | 调度函数 |
|---------|------|----------|
| `workflowStart` | 工作流入口 | dispatchWorkflowStart |
| `chatNode` | AI对话 | dispatchChatCompletion |
| `answerNode` | 回答节点 | dispatchAnswer |
| `datasetSearchNode` | 知识库搜索 | dispatchDatasetSearch |
| `datasetConcatNode` | 知识库拼接 | dispatchDatasetConcat |
| `ifElseNode` | 条件分支 | dispatchIfElse |
| `httpRequest468` | HTTP请求 | dispatchHttpRequest |
| `code` | 代码执行 | dispatchCode |
| `variableUpdate` | 变量更新 | dispatchVariableUpdate |
| `classifyQuestion` | 问题分类 | dispatchClassify |
| `contentExtract` | 内容提取 | dispatchContentExtract |
| `agent` | AI智能体 | dispatchRunTools |
| `userSelect` | 用户选择 | dispatchUserSelect |
| `formInput` | 表单输入 | dispatchFormInput |
| `loop/loopStart/loopEnd` | 循环控制 | dispatchLoop |
| `readFiles` | 文件读取 | dispatchReadFiles |
| `textEditor` | 文本编辑 | dispatchTextEditor |
| `pluginModule` | 插件模块 | dispatchPlugin |
| `appModule` | 应用模块 | dispatchApp |

### 2.2 节点输入输出类型

```typescript
enum FlowNodeInputTypeEnum {
  reference = 'reference',  // 引用其他节点
  input = 'input',         // 单行输入
  textarea = 'textarea',   // 多行文本
  switch = 'switch',       // 开关
  select = 'select',       // 下拉选择
  selectDataset = 'selectDataset',    // 知识库选择
  selectApp = 'selectApp',           // 应用选择
  selectLLMModel = 'selectLLMModel', // LLM模型选择
  JSONEditor = 'JSONEditor',          // JSON编辑器
  // ...
}

enum WorkflowIOValueTypeEnum {
  string = 'string',
  number = 'number',
  boolean = 'boolean',
  object = 'object',
  arrayString = 'arrayString',
  arrayObject = 'arrayObject',
  chatHistory = 'chatHistory',
  datasetQuote = 'datasetQuote',
  // ...
}
```

### 2.3 插件系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      FastGPT 插件系统                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │  插件模板     │   │  插件实例     │   │  工具集       │  │
│  │ (Template)   │   │ (Instance)   │   │  (Tools)     │  │
│  └──────────────┘   └──────────────┘   └──────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  API Endpoints:                                            │
│  - POST /api/v1/team/plugin/create    创建插件            │
│  - GET  /api/v1/team/plugin/list       获取插件列表        │
│  - POST /api/v1/team/plugin/update     更新插件            │
│  - DELETE /api/v1/team/plugin/delete   删除插件            │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 系统架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OpenCode-Agent 自动化系统                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              ComponentRegistry (组件注册中心)                  │    │
│  │  - fetchNodeTypes()      获取所有节点类型                    │    │
│  │  - fetchPlugins()        获取已安装插件                      │    │
│  │  - fetchTools()          获取可用工具                        │    │
│  │  - analyzeRequirements() 分析需求，识别缺失组件               │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                     │
│                              ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              CodeGenerator (代码生成器)                        │    │
│  │  - generatePluginCode()   生成插件后端代码                    │    │
│  │  - generatePluginConfig() 生成插件配置 (OpenAPI schema)       │    │
│  │  - validateCode()         验证生成的代码                      │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                     │
│                              ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              PluginManager (插件管理器)                        │    │
│  │  - createPlugin()        通过API创建插件实例                  │    │
│  │  - installPlugin()       安装插件到团队                       │    │
│  │  - getPluginId()        获取插件ID                           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                     │
│                              ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              WorkflowBuilder (工作流构建器)                    │    │
│  │  - buildWorkflow()       构建完整工作流                       │    │
│  │  - addNode()            添加节点                             │    │
│  │  - connectNodes()       连接节点                             │    │
│  │  - validateWorkflow()   验证工作流                           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 组件注册中心 (ComponentRegistry)

```typescript
interface ComponentRegistry {
  // 节点类型元数据
  nodes: Map<FlowNodeTypeEnum, NodeMetadata>;
  
  // 插件元数据
  plugins: Map<string, PluginMetadata>;
  
  // 工具元数据
  tools: Map<string, ToolMetadata>;
  
  // 获取所有可用组件
  async getAvailableComponents(): Promise<ComponentCatalog>;
  
  // 检查需求是否满足
  async checkRequirements(requirements: string[]): Promise<RequirementCheckResult>;
  
  // 识别缺失的组件
  async identifyMissingComponents(requirements: string[]): Promise<MissingComponent[]>;
}
```

### 3.3 代码生成器 (CodeGenerator)

```typescript
interface CodeGenerator {
  // 生成插件主代码
  generatePluginCode(spec: PluginSpec): GeneratedCode;
  
  // 生成 API 路由代码
  generateApiRoute(spec: PluginSpec): GeneratedRoute;
  
  // 生成前端配置 (用于插件注册)
  generatePluginConfig(spec: PluginSpec): PluginConfig;
  
  // 生成输入输出类型定义
  generateIOSchemas(spec: PluginSpec): IOSchema[];
}
```

### 3.4 插件管理器 (PluginManager)

```typescript
interface PluginManager {
  // 创建插件实例
  async createPlugin(config: PluginConfig): Promise<PluginInstance>;
  
  // 安装插件到团队
  async installPlugin(pluginId: string, teamId: string): Promise<void>;
  
  // 获取插件状态
  async getPluginStatus(pluginId: string): Promise<PluginStatus>;
  
  // 更新插件
  async updatePlugin(pluginId: string, config: Partial<PluginConfig>): Promise<void>;
}
```

### 3.5 工作流构建器 (WorkflowBuilder)

```typescript
interface WorkflowBuilder {
  // 创建工作流
  async build(spec: WorkflowSpec): Promise<WorkflowDefinition>;
  
  // 添加节点
  addNode(type: FlowNodeTypeEnum, config: NodeConfig): string; // returns nodeId
  
  // 连接节点
  connect(sourceId: string, targetId: string, sourceHandle?: string): void;
  
  // 设置节点输入
  setNodeInput(nodeId: string, inputName: string, value: any): void;
  
  // 导出工作流JSON
  export(): WorkflowJSON;
}
```

---

## 4. 核心流程设计

### 4.1 完整自动化流程

```
用户需求: "创建一个工作流，当用户询问股票价格时，调用我的股票API获取实时价格"
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────┐
│ Step 1: 需求分析与组件识别                                          │
├────────────────────────────────────────────────────────────────────┤
│  - 解析需求中的关键功能点                                           │
│  - 识别需要的组件: httpRequest468 (HTTP请求)                       │
│  - 识别条件逻辑: ifElseNode (条件分支)                             │
│  - 已有组件满足需求 ✓                                              │
└────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────┐
│ Step 2: 工作流构建                                                  │
├────────────────────────────────────────────────────────────────────┤
│  - workflowStart                                                   │
│  ├── classifyQuestion (识别"股票价格"意图)                         │
│  ├── httpRequest468 (调用股票API)                                  │
│  │   └── url: "https://api.stock.com/price?symbol={{symbol}}"    │
│  ├── ifElseNode                                                    │
│  │   ├── true: answerNode (返回价格)                              │
│  │   └── false: answerNode (股票未找到)                           │
│  └── answerNode                                                    │
└────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────┐
│ Step 3: 输出工作流 JSON                                             │
└────────────────────────────────────────────────────────────────────┘
```

### 4.2 需要自定义插件的流程

```
用户需求: "创建一个AI助手，调用我自定义的推荐算法"
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────┐
│ Step 1: 需求分析与组件识别                                          │
├────────────────────────────────────────────────────────────────────┤
│  - 识别需要的组件: 推荐算法 (自定义)                                 │
│  - 组件不存在 ✗                                                    │
│  - 需要生成自定义插件                                              │
└────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────┐
│ Step 2: 生成插件代码                                                │
├────────────────────────────────────────────────────────────────────┤
│  plugin/recommendation.py:                                         │
│  ```python                                                         │
│  class RecommendationPlugin:                                       │
│      def execute(user_id: str, items: list) -> list:              │
│          # 调用推荐算法                                            │
│          return recommendations                                    │
│  ```                                                               │
└────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────┐
│ Step 3: 创建插件实例 (通过 FastGPT API)                             │
├────────────────────────────────────────────────────────────────────┤
│  POST /api/v1/team/plugin/create                                   │
│  {                                                                 │
│    "name": "推荐算法插件",                                         │
│    "description": "基于用户历史的推荐算法",                        │
│    "inputs": [{"name": "userId", "type": "string"},               │
│                {"name": "items", "type": "array"}],               │
│    "outputs": [{"name": "recommendations", "type": "array"}]      │
│  }                                                                 │
└────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────┐
│ Step 4: 工作流构建                                                  │
├────────────────────────────────────────────────────────────────────┤
│  - workflowStart                                                   │
│  ├── pluginModule (使用刚创建的推荐插件)                            │
│  ├── chatNode (生成推荐理由)                                       │
│  └── answerNode                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 5. 实现细节

### 5.1 组件发现服务

```typescript
// src/services/component_registry.ts
export class ComponentRegistry {
  private static instance: ComponentRegistry;
  private nodes: Map<string, NodeMetadata>;
  private plugins: Map<string, PluginMetadata>;
  
  static getInstance(): ComponentRegistry {
    if (!ComponentRegistry.instance) {
      ComponentRegistry.instance = new ComponentRegistry();
    }
    return ComponentRegistry.instance;
  }
  
  // 从 FastGPT API 获取节点类型
  async fetchNodeTypes(): Promise<void> {
    // 静态解析 FlowNodeTypeEnum
    const nodeTypes = [
      'workflowStart', 'chatNode', 'answerNode', 
      'datasetSearchNode', 'httpRequest468', 'ifElseNode',
      // ... 40+ types
    ];
    
    for (const type of nodeTypes) {
      this.nodes.set(type, await this.getNodeMetadata(type));
    }
  }
  
  // 获取已安装插件
  async fetchPlugins(teamId: string): Promise<PluginMetadata[]> {
    const response = await fetch(`/api/v1/team/plugin/list`, {
      headers: { 'Authorization': `Bearer ${apiKey}` }
    });
    return response.json();
  }
  
  // 分析需求，识别需要的组件
  async analyzeRequirements(requirements: string[]): Promise<AnalysisResult> {
    const analyzer = new RequirementAnalyzer(this.nodes, this.plugins);
    return analyzer.analyze(requirements);
  }
}
```

### 5.2 插件代码生成器

```typescript
// src/services/code_generator.ts
export class PluginCodeGenerator {
  generatePlugin(spec: PluginSpec): GeneratedPlugin {
    return {
      // 1. 主代码文件
      mainFile: this.generateMainFile(spec),
      
      // 2. API 路由 (如果需要 HTTP 入口)
      routeFile: spec.needsHttpEndpoint 
        ? this.generateRouteFile(spec) 
        : null,
      
      // 3. 插件配置 (用于注册到 FastGPT)
      configFile: this.generateConfigFile(spec),
      
      // 4. 测试文件
      testFile: this.generateTestFile(spec),
    };
  }
  
  private generateMainFile(spec: PluginSpec): string {
    return `
import { PluginBase } from '@fastgpt/service/core/plugin/base';

export class ${toPascalCase(spec.name)}Plugin extends PluginBase {
  async execute(inputs: ${this.generateInputType(spec)}): Promise<${this.generateOutputType(spec)}> {
    // TODO: 实现你的业务逻辑
    ${spec.implementation}
  }
}

export default ${toPascalCase(spec.name)}Plugin;
`;
  }
  
  private generateConfigFile(spec: PluginSpec): PluginRegistrationConfig {
    return {
      name: spec.name,
      description: spec.description,
      version: '1.0.0',
      inputs: spec.inputs.map(input => ({
        name: input.name,
        type: input.type,
        required: input.required,
        description: input.description,
      })),
      outputs: spec.outputs.map(output => ({
        name: output.name,
        type: output.type,
        description: output.description,
      })),
    };
  }
}
```

### 5.3 插件管理器

```typescript
// src/services/plugin_manager.ts
export class PluginManager {
  constructor(private apiKey: string, private teamId: string) {}
  
  // 创建插件实例
  async createPlugin(config: PluginRegistrationConfig): Promise<PluginInstance> {
    const response = await fetch('/api/v1/team/plugin/create', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ...config,
        teamId: this.teamId,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to create plugin: ${response.statusText}`);
    }
    
    return response.json();
  }
  
  // 安装插件到团队
  async installPlugin(pluginId: string): Promise<void> {
    await fetch(`/api/v1/team/plugin/${pluginId}/install`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${this.apiKey}` },
    });
  }
}
```

### 5.4 工作流构建器

```typescript
// src/services/workflow_builder.ts
export class WorkflowBuilder {
  private nodes: FlowNodeItemType[] = [];
  private edges: FlowEdgeItemType[] = [];
  private nodeIdCounter = 0;
  
  addNode(type: FlowNodeTypeEnum, config: Partial<FlowNodeItemType>): string {
    const nodeId = `${type}_${++this.nodeIdCounter}`;
    
    const node: FlowNodeItemType = {
      nodeId,
      flowNodeType: type,
      position: config.position ?? { x: 0, y: 0 },
      data: {
        ...getDefaultNodeData(type),
        ...config.data,
      },
      ...config,
    };
    
    this.nodes.push(node);
    return nodeId;
  }
  
  connect(sourceId: string, targetId: string, sourceHandle?: string): void {
    this.edges.push({
      source: sourceId,
      target: targetId,
      sourceHandle: sourceHandle ?? 'source',
      targetHandle: 'target',
    });
  }
  
  export(): WorkflowDefinition {
    return {
      nodes: this.nodes,
      edges: this.edges,
    };
  }
}
```

---

## 6. API 设计

### 6.1 OpenCode-Agent 内部 API

```typescript
// 创建工作流请求
interface CreateWorkflowRequest {
  requirements: string;          // 用户需求描述
  options?: {
    autoGeneratePlugin?: boolean; // 是否自动生成缺失插件
    validateOnly?: boolean;       // 仅验证，不创建
  };
}

// 创建工作流响应
interface CreateWorkflowResponse {
  workflow: WorkflowDefinition;
  usedComponents: ComponentUsage[];
  generatedPlugins?: GeneratedPluginInfo[];
  validation: ValidationResult;
}
```

### 6.2 与 FastGPT API 集成

```typescript
// FastGPT 插件创建 API (参考现有模式)
interface FastGPTPluginAPI {
  // 创建插件
  create: POST /api/v1/team/plugin/create {
    name: string;
    description: string;
    inputs: IOField[];
    outputs: IOField[];
  } => { pluginId: string };
  
  // 获取插件列表
  list: GET /api/v1/team/plugin/list => PluginInfo[];
  
  // 更新插件
  update: PUT /api/v1/team/plugin/:id;
  
  // 删除插件
  delete: DELETE /api/v1/team/plugin/:id;
  
  // 插件市场
  market: GET /api/v1/plugin/market => PluginTemplate[];
}
```

---

## 7. 错误处理与验证

### 7.1 验证层次

```typescript
interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

class WorkflowValidator {
  validateWorkflow(workflow: WorkflowDefinition): ValidationResult {
    const errors: ValidationError[] = [];
    
    // 1. 检查入口节点
    const entryNodes = workflow.nodes.filter(n => n.data.isEntry);
    if (entryNodes.length === 0) {
      errors.push({ code: 'NO_ENTRY', message: '工作流缺少入口节点' });
    }
    
    // 2. 检查孤立节点
    const connectedNodeIds = new Set(
      workflow.edges.flatMap(e => [e.source, e.target])
    );
    for (const node of workflow.nodes) {
      if (!connectedNodeIds.has(node.nodeId)) {
        errors.push({ 
          code: 'ORPHAN_NODE', 
          message: `节点 ${node.nodeId} 未连接到任何节点` 
        });
      }
    }
    
    // 3. 检查数据类型兼容性
    // ...
    
    return { valid: errors.length === 0, errors, warnings: [] };
  }
}
```

---

## 8. 测试策略

### 8.1 单元测试

```typescript
// tests/test_component_registry.ts
describe('ComponentRegistry', () => {
  it('should fetch all node types', async () => {
    const registry = ComponentRegistry.getInstance();
    await registry.fetchNodeTypes();
    expect(registry.nodes.size).toBeGreaterThan(40);
  });
  
  it('should identify missing components', async () => {
    const registry = ComponentRegistry.getInstance();
    const missing = await registry.identifyMissingComponents([
      '股票API', '推荐算法'
    ]);
    expect(missing.length).toBe(2);
  });
});

// tests/test_code_generator.ts
describe('PluginCodeGenerator', () => {
  it('should generate valid plugin code', () => {
    const generator = new PluginCodeGenerator();
    const code = generator.generatePlugin({
      name: 'test-plugin',
      inputs: [{ name: 'input', type: 'string' }],
      outputs: [{ name: 'output', type: 'string' }],
      implementation: 'return inputs.input;',
    });
    
    expect(code.mainFile).toContain('class TestPlugin');
    expect(code.configFile.name).toBe('test-plugin');
  });
});
```

---

## 9. 实施计划

### Phase 1: 组件发现 (1周)
- [ ] 实现 ComponentRegistry
- [ ] 集成 FastGPT API 获取插件列表
- [ ] 实现需求分析器

### Phase 2: 代码生成 (1周)
- [ ] 实现 PluginCodeGenerator
- [ ] 生成 Python/TypeScript 插件模板
- [ ] 生成 OpenAPI schema

### Phase 3: 插件管理 (1周)
- [ ] 实现 PluginManager
- [ ] 集成 FastGPT 插件创建 API
- [ ] 实现插件安装流程

### Phase 4: 工作流构建 (1周)
- [ ] 实现 WorkflowBuilder
- [ ] 实现节点连接和数据绑定
- [ ] 实现工作流验证

### Phase 5: 集成测试 (1周)
- [ ] 端到端流程测试
- [ ] 错误处理测试
- [ ] 性能优化

---

## 10. 文件结构

```
projects/opencode-agent/
├── src/
│   ├── services/
│   │   ├── component_registry.ts    # 组件注册中心
│   │   ├── code_generator.ts       # 代码生成器
│   │   ├── plugin_manager.ts       # 插件管理器
│   │   └── workflow_builder.ts     # 工作流构建器
│   ├── types/
│   │   ├── components.ts           # 组件类型定义
│   │   ├── workflow.ts             # 工作流类型定义
│   │   └── plugin.ts               # 插件类型定义
│   ├── utils/
│   │   ├── fastgpt_api.ts         # FastGPT API 客户端
│   │   └── validators.ts           # 验证工具
│   └── main.ts                     # 入口文件
├── tests/
│   ├── test_component_registry.ts
│   ├── test_code_generator.ts
│   ├── test_plugin_manager.ts
│   └── test_workflow_builder.ts
└── package.json
```

---

## 11. 总结

本设计文档详细阐述了如何实现：

1. **组件发现**: 实时获取 FastGPT 的 40+ 节点类型和已安装插件
2. **智能分析**: 自动分析用户需求，识别需要的工作流组件
3. **代码生成**: 当组件不存在时，自动生成插件后端代码
4. **插件管理**: 通过 API 在 FastGPT 中创建和管理插件实例
5. **工作流构建**: 组装完整的工作流定义 JSON

这套系统实现了从"用户需求"到"可运行工作流"的完整自动化闭环。
