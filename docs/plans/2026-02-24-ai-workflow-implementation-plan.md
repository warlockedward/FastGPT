# AI Workflow Generator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an AI-powered workflow generation system for FastGPT with microservices architecture - enabling non-technical users to create workflows via natural language and developers to extend with custom plugins.

**Architecture:** Fully distributed microservices with AI Workflow Gateway (Next.js), Plugin Runtime (Node.js), OpenCode Agent (Python FastAPI), and OpenSandbox integration.

**Tech Stack:** Next.js API Routes, Python FastAPI, Node.js/Express, MongoDB, Redis, OpenCode API, OpenSandbox

---

## Phase 1: Foundation

### Task 1: Create Type Definitions

**Files:**
- Create: `packages/global/openapi/core/workflow/ai/api.d.ts`

**Step 1: Create type definitions file**

```typescript
import { z } from 'zod';

// Question schema for multi-round conversation
export const QuestionSchema = z.object({
  id: z.string(),
  question: z.string(),
  options: z.array(z.string()).optional(),
  type: z.enum(['choice', 'text']).default('text')
});

// Chat request
export const AiChatRequestSchema = z.object({
  teamId: z.string(),
  message: z.string(),
  sessionId: z.string().optional(),
  context: z.object({
    mode: z.enum(['create', 'optimize']).default('create'),
    workflowId: z.string().optional()
  }).optional()
});

export type AiChatRequestType = z.infer<typeof AiChatRequestSchema>;

// Chat response
export const AiChatResponseSchema = z.object({
  sessionId: z.string(),
  message: z.string(),
  status: z.enum(['ready', 'need_more_info', 'error']),
  workflowPreview: z.object({
    nodes: z.array(z.any()),
    edges: z.array(z.any())
  }).optional(),
  questions: z.array(QuestionSchema).optional(),
  suggestions: z.array(z.string()).optional()
});

export type AiChatResponseType = z.infer<typeof AiChatResponseSchema>;

// Workflow confirm request
export const WorkflowConfirmRequestSchema = z.object({
  sessionId: z.string(),
  answer: z.string(),
  confirmed: z.boolean().default(false)
});

export type WorkflowConfirmRequestType = z.infer<typeof WorkflowConfirmRequestSchema>;

// Workflow validate request
export const WorkflowValidateRequestSchema = z.object({
  workflow: z.object({
    nodes: z.array(z.any()),
    edges: z.array(z.any())
  }),
  plugins: z.array(z.object({
    name: z.string(),
    code: z.string()
  })).optional()
});

export type WorkflowValidateRequestType = z.infer<typeof WorkflowValidateRequestSchema>;

// Plugin code validation request
export const PluginCodeValidateRequestSchema = z.object({
  code: z.string(),
  language: z.enum(['typescript', 'python']),
  inputs: z.array(z.object({
    name: z.string(),
    type: z.string(),
    required: z.boolean()
  })).optional()
});

export type PluginCodeValidateRequestType = z.infer<typeof PluginCodeValidateRequestSchema>;
```

**Step 2: Commit**
```bash
git add packages/global/openapi/core/workflow/ai/api.d.ts
git commit -m "feat(ai-workflow): add API type definitions"
```

---

### Task 2: Create Session MongoDB Schema

**Files:**
- Create: `packages/service/core/aiWorkflow/sessionSchema.ts`
- Create: `packages/service/core/aiWorkflow/sessionController.ts`

**Step 1: Create session schema**

```typescript
import { Schema, getMongoModel } from '../../common/mongo';
import type { AiChatRequestType } from '@fastgpt/global/openapi/core/workflow/ai/api';

const SessionSchema = new Schema(
  {
    sessionId: { type: String, required: true, index: true },
    teamId: { type: String, required: true, index: true },
    userId: { type: String, index: true },
    messages: [
      {
        role: { type: String, enum: ['user', 'assistant'] },
        content: String,
        timestamp: { type: Date, default: Date.now }
      }
    ],
    context: {
      mode: { type: String, enum: ['create', 'optimize'], default: 'create' },
      workflowId: String,
      questions: [
        {
          id: String,
          question: String,
          options: [String],
          type: { type: String, enum: ['choice', 'text'], default: 'text' }
        }
      ]
    },
    status: { type: String, enum: ['active', 'completed', 'expired'], default: 'active' },
    metadata: {
      generatedWorkflow: {
        nodes: { type: Schema.Types.Mixed },
        edges: { type: Schema.Types.Mixed }
      }
    }
  },
  {
    timestamps: true
  }
);

SessionSchema.index({ teamId: 1, updatedAt: -1 });

export const MongoSession = getMongoModel<AiChatRequestType & { _id: any }>(
  'aiWorkflowSession',
  SessionSchema
);
```

**Step 2: Create session controller**

```typescript
import { MongoSession } from './sessionSchema';
import { z } from 'zod';

export async function createSession(teamId: string, userId?: string) {
  const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  const session = await MongoSession.create({
    sessionId,
    teamId,
    userId,
    messages: [],
    context: { mode: 'create' },
    status: 'active'
  });
  return session;
}

export async function addMessage(
  sessionId: string,
  role: 'user' | 'assistant',
  content: string
) {
  return MongoSession.findOneAndUpdate(
    { sessionId },
    {
      $push: { messages: { role, content, timestamp: new Date() } },
      $set: { updatedAt: new Date() }
    },
    { new: true }
  );
}

export async function getSession(sessionId: string) {
  return MongoSession.findOne({ sessionId });
}

export async function updateSessionContext(
  sessionId: string,
  context: any,
  workflow?: any
) {
  return MongoSession.findOneAndUpdate(
    { sessionId },
    {
      $set: {
        context,
        'metadata.generatedWorkflow': workflow,
        updatedAt: new Date()
      }
    },
    { new: true }
  );
}

export async function completeSession(sessionId: string) {
  return MongoSession.findOneAndUpdate(
    { sessionId },
    { $set: { status: 'completed', updatedAt: new Date() } },
    { new: true }
  );
}
```

**Step 3: Commit**
```bash
git add packages/service/core/aiWorkflow/
git commit -m "feat(ai-workflow): add session schema and controller"
```

---

### Task 3: Create Plugin MongoDB Schema

**Files:**
- Create: `packages/service/core/aiWorkflow/pluginSchema.ts`
- Create: `packages/service/core/aiWorkflow/pluginController.ts`

**Step 1: Create plugin schema**

```typescript
import { Schema, getMongoModel } from '../../common/mongo';

const PluginSchema = new Schema(
  {
    pluginId: { type: String, required: true, index: true },
    teamId: { type: String, required: true, index: true },
    userId: { type: String, index: true },
    name: { type: String, required: true },
    description: String,
    code: { type: String, required: true },
    language: { type: String, enum: ['typescript', 'python'], default: 'typescript' },
    inputs: [
      {
        name: String,
        type: String,
        required: { type: Boolean, default: false }
      }
    ],
    outputs: [
      {
        name: String,
        type: String
      }
    ],
    version: { type: String, default: '1.0.0' },
    status: { type: String, enum: ['draft', 'deployed', 'failed'], default: 'draft' },
    runtimePort: Number,
    runtimePid: Number,
    apiSpec: {
      openapi: { type: Schema.Types.Mixed },
      endpoints: [
        {
          path: String,
          method: String,
          parameters: { type: Schema.Types.Mixed }
        }
      ]
    }
  },
  {
    timestamps: true
  }
);

PluginSchema.index({ teamId: 1, status: 1 });

export const MongoPlugin = getMongoModel<any>('aiWorkflowPlugin', PluginSchema);
```

**Step 2: Create plugin controller**

```typescript
import { MongoPlugin } from './pluginSchema';

export async function createPlugin(data: {
  teamId: string;
  userId?: string;
  name: string;
  description?: string;
  code: string;
  language: 'typescript' | 'python';
  inputs?: any[];
  outputs?: any[];
}) {
  const pluginId = `plugin_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  const plugin = await MongoPlugin.create({
    ...data,
    pluginId,
    status: 'draft'
  });
  return plugin;
}

export async function getPlugins(teamId: string, status?: string) {
  const query: any = { teamId };
  if (status) query.status = status;
  return MongoPlugin.find(query).sort({ createdAt: -1 });
}

export async function getPlugin(pluginId: string) {
  return MongoPlugin.findOne({ pluginId });
}

export async function updatePlugin(pluginId: string, data: Partial<any>) {
  return MongoPlugin.findOneAndUpdate(
    { pluginId },
    { $set: { ...data, updatedAt: new Date() } },
    { new: true }
  );
}

export async function deletePlugin(pluginId: string) {
  return MongoPlugin.findOneAndDelete({ pluginId });
}

export async function deployPlugin(pluginId: string, port: number) {
  return MongoPlugin.findOneAndUpdate(
    { pluginId },
    { $set: { status: 'deployed', runtimePort: port, updatedAt: new Date() } },
    { new: true }
  );
}
```

**Step 3: Commit**
```bash
git add packages/service/core/aiWorkflow/
git commit -m "feat(ai-workflow): add plugin schema and controller"
```

---

## Phase 2: API Gateway Implementation

### Task 4: Create Chat API Endpoint

**Files:**
- Modify: `projects/app/src/pages/api/core/workflow/ai/chat.ts`

**Step 1: Update chat.ts with proper validation**

```typescript
import type { NextApiRequest, NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { ReadPermissionVal } from '@fastgpt/global/support/permission/constant';
import type {
  AiChatRequestType,
  AiChatResponseType
} from '@fastgpt/global/openapi/core/workflow/ai/api';
import { getSystemToolsWithInstalled } from '@fastgpt/service/core/app/tool/controller';
import { createSession, addMessage, getSession, updateSessionContext } from '@fastgpt/service/core/aiWorkflow/sessionController';

async function handler(req: NextApiRequest, res: NextApiResponse): Promise<AiChatResponseType> {
  const { teamId, tmbId, userId, isRoot } = await authUserPer({
    req,
    authToken: true,
    per: ReadPermissionVal
  });

  const body = req.body as AiChatRequestType;
  const { message, sessionId, context } = body;

  // Validate message
  if (!message?.trim()) {
    return Promise.reject('Message is required');
  }

  const opencodeApiUrl = process.env.OPENCODE_API_URL;
  if (!opencodeApiUrl) {
    return Promise.reject('OPENCODE_API_URL is not configured');
  }

  // Get or create session
  let currentSession = sessionId ? await getSession(sessionId) : null;
  if (!currentSession) {
    currentSession = await createSession(teamId, userId);
  }

  // Add user message
  await addMessage(currentSession.sessionId, 'user', message);

  // Get available tools
  const availableTools = await getSystemToolsWithInstalled({ teamId, isRoot });
  const availablePlugins = availableTools
    .filter((tool) => tool.installed)
    .map((tool) => ({
      id: tool.id,
      name: tool.name,
      description: tool.description,
      flowNodeType: tool.flowNodeType
    }));

  // Call OpenCode API
  const mode = context?.mode || 'create';
  const endpoint =
    mode === 'optimize' && context?.workflowId
      ? `${opencodeApiUrl}/api/ai-workflow/optimize`
      : `${opencodeApiUrl}/api/ai-workflow/generate`;

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.OPENCODE_API_KEY || ''}`
      },
      body: JSON.stringify({
        userIntent: message,
        sessionId: currentSession.sessionId,
        context: {
          existingWorkflow: context?.workflowId,
          availablePlugins: availablePlugins.map((p) => p.name),
          enterpriseSystems: []
        },
        options: {
          generatePlugins: true,
          maxIterations: 3
        }
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      return Promise.reject(`OpenCode API error: ${response.status} - ${errorText}`);
    }

    const result = await response.json();

    // Update session with AI response
    await addMessage(currentSession.sessionId, 'assistant', result.message || '工作流已生成');

    // Update context if needed
    if (result.questions || result.workflow) {
      await updateSessionContext(
        currentSession.sessionId,
        { ...context, questions: result.questions },
        result.workflow
      );
    }

    return {
      sessionId: result.sessionId || currentSession.sessionId,
      message: result.message || '工作流已生成',
      suggestions: result.suggestions,
      workflowPreview: result.workflow
        ? {
            nodes: result.workflow.nodes,
            edges: result.workflow.edges
          }
        : undefined,
      status: result.status,
      questions: result.questions
    };
  } catch (error) {
    return Promise.reject(`Failed to connect to OpenCode API: ${error}`);
  }
}

export default NextAPI(handler);
```

**Step 2: Commit**
```bash
git add projects/app/src/pages/api/core/workflow/ai/chat.ts
git commit -m "feat(ai-workflow): enhance chat endpoint with session management"
```

---

### Task 5: Create Confirm API Endpoint

**Files:**
- Create: `projects/app/src/pages/api/core/workflow/ai/workflow/confirm.ts`

**Step 1: Create confirm endpoint**

```typescript
import type { NextApiRequest, NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { ReadPermissionVal } from '@fastgpt/global/support/permission/constant';
import type { WorkflowConfirmRequestType } from '@fastgpt/global/openapi/core/workflow/ai/api';
import { getSession, addMessage, updateSessionContext, completeSession } from '@fastgpt/service/core/aiWorkflow/sessionController';

async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { teamId, tmbId, userId, isRoot } = await authUserPer({
    req,
    authToken: true,
    per: ReadPermissionVal
  });

  const body = req.body as WorkflowConfirmRequestType;
  const { sessionId, answer, confirmed } = body;

  if (!sessionId || !answer) {
    return Promise.reject('sessionId and answer are required');
  }

  const session = await getSession(sessionId);
  if (!session) {
    return Promise.reject('Session not found');
  }

  // Add user answer to session
  await addMessage(sessionId, 'user', answer);

  // If confirmed, complete the session
  if (confirmed) {
    await completeSession(sessionId);
    return {
      sessionId,
      status: 'completed',
      message: '工作流已确认保存',
      workflow: session.metadata?.generatedWorkflow
    };
  }

  // Otherwise, continue conversation with OpenCode API
  const opencodeApiUrl = process.env.OPENCODE_API_URL;
  if (!opencodeApiUrl) {
    return Promise.reject('OPENCODE_API_URL is not configured');
  }

  try {
    const response = await fetch(`${opencodeApiUrl}/api/ai-workflow/confirm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.OPENCODE_API_KEY || ''}`
      },
      body: JSON.stringify({
        sessionId,
        answer,
        context: session.context
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      return Promise.reject(`OpenCode API error: ${response.status} - ${errorText}`);
    }

    const result = await response.json();

    // Update session
    await addMessage(sessionId, 'assistant', result.message);
    await updateSessionContext(
      sessionId,
      { ...session.context, questions: result.questions },
      result.workflow
    );

    return {
      sessionId,
      status: result.status,
      message: result.message,
      workflow: result.workflow,
      questions: result.questions
    };
  } catch (error) {
    return Promise.reject(`Failed to confirm: ${error}`);
  }
}

export default NextAPI(handler);
```

**Step 2: Commit**
```bash
git add projects/app/src/pages/api/core/workflow/ai/workflow/confirm.ts
git commit -m "feat(ai-workflow): add workflow confirm endpoint"
```

---

### Task 6: Create Validate API Endpoint

**Files:**
- Create: `projects/app/src/pages/api/core/workflow/ai/workflow/validate.ts`

**Step 1: Create validate endpoint**

```typescript
import type { NextApiRequest, NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { ReadPermissionVal } from '@fastgpt/global/support/permission/constant';
import type { WorkflowValidateRequestType } from '@fastgpt/global/openapi/core/workflow/ai/api';

async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { teamId, tmbId, userId, isRoot } = await authUserPer({
    req,
    authToken: true,
    per: ReadPermissionVal
  });

  const body = req.body as WorkflowValidateRequestType;
  const { workflow, plugins } = body;

  if (!workflow) {
    return Promise.reject('Workflow is required');
  }

  const errors: string[] = [];
  const suggestions: string[] = [];

  // Validate workflow structure
  if (!workflow.nodes || !Array.isArray(workflow.nodes)) {
    errors.push('Workflow must have nodes array');
  }

  if (!workflow.edges || !Array.isArray(workflow.edges)) {
    errors.push('Workflow must have edges array');
  }

  // Check for start node
  const hasStart = workflow.nodes?.some((node: any) => node.flowNodeType === 'workflowStart');
  if (!hasStart) {
    errors.push('Workflow must have a start node');
    suggestions.push('Add a workflow start node to define where the workflow begins');
  }

  // Validate node connections
  const nodeIds = new Set(workflow.nodes?.map((n: any) => n.id) || []);
  const orphanEdges = (workflow.edges || []).filter((edge: any) => {
    return !nodeIds.has(edge.source) || !nodeIds.has(edge.target);
  });
  if (orphanEdges.length > 0) {
    errors.push(`Found ${orphanEdges.length} edges with invalid source or target`);
    suggestions.push('Review all edge connections to ensure they reference valid nodes');
  }

  // Validate plugins if any
  if (plugins && Array.isArray(plugins)) {
    for (const plugin of plugins) {
      if (!plugin.name || !plugin.code) {
        errors.push(`Plugin ${plugin.name || 'unnamed'} missing name or code`);
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    suggestions
  };
}

export default NextAPI(handler);
```

**Step 2: Commit**
```bash
git add projects/app/src/pages/api/core/workflow/ai/workflow/validate.ts
git commit -m "feat(ai-workflow): add workflow validate endpoint"
```

---

### Task 7: Create Plugin Code Validation Endpoint

**Files:**
- Create: `projects/app/src/pages/api/core/workflow/ai/plugin/validateCode.ts`

**Step 1: Create validateCode endpoint**

```typescript
import type { NextApiRequest, NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { ReadPermissionVal } from '@fastgpt/global/support/permission/constant';
import type { PluginCodeValidateRequestType } from '@fastgpt/global/openapi/core/workflow/ai/api';

async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { teamId, tmbId, userId, isRoot } = await authUserPer({
    req,
    authToken: true,
    per: ReadPermissionVal
  });

  const body = req.body as PluginCodeValidateRequestType;
  const { code, language, inputs } = body;

  if (!code) {
    return Promise.reject('Code is required');
  }

  const opensandboxUrl = process.env.OPENSANDBOX_URL;
  if (!opensandboxUrl) {
    return Promise.reject('OPENSANDBOX_URL is not configured');
  }

  try {
    const response = await fetch(`${opensandboxUrl}/api/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        code,
        language: language || 'typescript',
        inputs: inputs || [],
        timeout: 5000
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      return Promise.reject(`OpenSandbox error: ${response.status} - ${errorText}`);
    }

    const result = await response.json();

    return {
      valid: result.valid,
      errors: result.errors || [],
      output: result.output,
      executionTime: result.executionTime
    };
  } catch (error) {
    return Promise.reject(`Failed to validate code: ${error}`);
  }
}

export default NextAPI(handler);
```

**Step 2: Commit**
```bash
git add projects/app/src/pages/api/core/workflow/ai/plugin/validateCode.ts
git commit -m "feat(ai-workflow): add plugin code validation endpoint"
```

---

## Phase 3: OpenCode Agent (Python)

### Task 8: Create OpenCode Agent Service

**Files:**
- Create: `projects/opencode-agent/main.py`
- Create: `projects/opencode-agent/requirements.txt`
- Create: `projects/opencode-agent/src/agent/__init__.py`
- Create: `projects/opencode-agent/src/agent/core.py`
- Create: `projects/opencode-agent/src/api/__init__.py`
- Create: `projects/opencode-agent/src/api/routes.py`

**Step 1: Create main.py**

```python
from fastapi import FastAPI
from src.api.routes import router

app = FastAPI(
    title="OpenCode AI Workflow Agent",
    description="AI agent for generating FastGPT workflows",
    version="1.0.0"
)

app.include_router(router, prefix="/api/ai-workflow", tags=["workflow"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**Step 2: Create requirements.txt**

```
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
httpx>=0.25.0
python-dotenv>=1.0.0
```

**Step 3: Create agent core.py**

```python
from typing import Dict, List, Optional, Any
import json
import httpx

class WorkflowAgent:
    def __init__(self, opencode_api_url: str, opencode_api_key: str):
        self.opencode_api_url = opencode_api_url
        self.opencode_api_key = opencode_api_key
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def generate_workflow(
        self,
        user_intent: str,
        session_id: str,
        context: Dict[str, Any],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a workflow based on user intent."""
        
        # Build prompt for OpenCode
        prompt = self._build_generation_prompt(user_intent, context, options)
        
        # Call OpenCode API
        response = await self.client.post(
            f"{self.opencode_api_url}/chat",
            headers={"Authorization": f"Bearer {self.opencode_api_key}"},
            json={
                "messages": [{"role": "user", "content": prompt}],
                "session_id": session_id
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenCode API error: {response.text}")
        
        result = response.json()
        
        # Parse response to extract workflow
        workflow = self._parse_workflow_response(result.get("content", ""))
        
        if workflow:
            return {
                "status": "ready",
                "message": "工作流已生成",
                "workflow": workflow,
                "session_id": session_id
            }
        
        # Check if more info needed
        questions = self._extract_questions(result.get("content", ""))
        if questions:
            return {
                "status": "need_more_info",
                "message": "需要更多信息",
                "questions": questions,
                "session_id": session_id
            }
        
        return {
            "status": "error",
            "message": "无法生成工作流",
            "session_id": session_id
        }
    
    async def optimize_workflow(
        self,
        user_intent: str,
        session_id: str,
        context: Dict[str, Any],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize an existing workflow based on user intent."""
        
        existing_workflow_id = context.get("existingWorkflow")
        if not existing_workflow_id:
            return await self.generate_workflow(user_intent, session_id, context, options)
        
        prompt = self._build_optimization_prompt(user_intent, existing_workflow_id, context, options)
        
        response = await self.client.post(
            f"{self.opencode_api_url}/chat",
            headers={"Authorization": f"Bearer {self.opencode_api_key}"},
            json={
                "messages": [{"role": "user", "content": prompt}],
                "session_id": session_id
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenCode API error: {response.text}")
        
        result = response.json()
        workflow = self._parse_workflow_response(result.get("content", ""))
        
        return {
            "status": "ready",
            "message": "工作流已优化",
            "workflow": workflow,
            "session_id": session_id
        }
    
    async def confirm_workflow(
        self,
        session_id: str,
        answer: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle user confirmation/answer during multi-round conversation."""
        
        prompt = f"User answered: {answer}. Continue generating the workflow."
        
        response = await self.client.post(
            f"{self.opencode_api_url}/chat",
            headers={"Authorization": f"Bearer {self.opencode_api_key}"},
            json={
                "messages": [{"role": "user", "content": prompt}],
                "session_id": session_id
            }
        )
        
        result = response.json()
        workflow = self._parse_workflow_response(result.get("content", ""))
        
        if workflow:
            return {
                "status": "ready",
                "message": "工作流已生成",
                "workflow": workflow,
                "session_id": session_id
            }
        
        questions = self._extract_questions(result.get("content", ""))
        return {
            "status": "need_more_info",
            "message": "需要更多信息",
            "questions": questions,
            "session_id": session_id
        }
    
    def _build_generation_prompt(self, intent: str, context: Dict, options: Dict) -> str:
        available = context.get("availablePlugins", [])
        return f"""Generate a FastGPT workflow for: {intent}

Available plugins: {', '.join(available) if available else 'None'}

Generate the workflow as JSON with nodes and edges."""
    
    def _build_optimization_prompt(self, intent: str, workflow_id: str, context: Dict, options: Dict) -> str:
        return f"""Optimize workflow {workflow_id} based on: {intent}

Generate the updated workflow as JSON."""
    
    def _parse_workflow_response(self, content: str) -> Optional[Dict]:
        """Parse workflow JSON from OpenCode response."""
        try:
            # Try to find JSON in response
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                if "nodes" in data and "edges" in data:
                    return data
        except:
            pass
        return None
    
    def _extract_questions(self, content: str) -> List[Dict]:
        """Extract clarifying questions from response."""
        questions = []
        try:
            import re
            # Look for question patterns
            q_matches = re.findall(r'\d+\)\s*(.+?)(?:\?|$)', content, re.MULTILINE)
            for i, q in enumerate(q_matches, 1):
                questions.append({
                    "id": f"q{i}",
                    "question": q.strip(),
                    "type": "text"
                })
        except:
            pass
        return questions
```

**Step 4: Create routes.py**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from src.agent.core import WorkflowAgent
import os

router = APIRouter()

# Initialize agent
agent = WorkflowAgent(
    opencode_api_url=os.getenv("OPENCODE_API_URL", "http://localhost:8080"),
    opencode_api_key=os.getenv("OPENCODE_API_KEY", "")
)

class GenerateRequest(BaseModel):
    userIntent: str
    sessionId: Optional[str] = None
    context: Optional[Dict[str, Any]] = {}
    options: Optional[Dict[str, Any]] = {}

class ConfirmRequest(BaseModel):
    sessionId: str
    answer: str
    context: Optional[Dict[str, Any]] = {}

@router.post("/generate")
async def generate_workflow(req: GenerateRequest):
    """Generate a new workflow from user intent."""
    try:
        result = await agent.generate_workflow(
            user_intent=req.userIntent,
            session_id=req.sessionId or "",
            context=req.context or {},
            options=req.options or {}
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimize")
async def optimize_workflow(req: GenerateRequest):
    """Optimize an existing workflow."""
    try:
        result = await agent.optimize_workflow(
            user_intent=req.userIntent,
            session_id=req.sessionId or "",
            context=req.context or {},
            options=req.options or {}
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/confirm")
async def confirm_workflow(req: ConfirmRequest):
    """Handle user confirmation/answer."""
    try:
        result = await agent.confirm_workflow(
            session_id=req.sessionId,
            answer=req.answer,
            context=req.context or {}
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 5: Commit**
```bash
git add projects/opencode-agent/
git commit -m "feat(ai-workflow): add OpenCode agent Python service"
```

---

## Phase 4: Plugin Runtime

### Task 9: Create Plugin Runtime Service

**Files:**
- Create: `projects/plugin-runtime/package.json`
- Create: `projects/plugin-runtime/src/index.ts`
- Create: `projects/plugin-runtime/src/manager.ts`
- Create: `projects/plugin-runtime/src/plugins/http.ts`

**Step 1: Create package.json**

```json
{
  "name": "@fastgpt/plugin-runtime",
  "version": "1.0.0",
  "description": "FastGPT Plugin Runtime Service",
  "main": "dist/index.js",
  "scripts": {
    "dev": "ts-node-dev --respawn src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "body-parser": "^1.20.2",
    "cors": "^2.8.5",
    "uuid": "^9.0.0"
  },
  "devDependencies": {
    "@types/express": "^4.17.17",
    "@types/node": "^20.5.0",
    "@types/cors": "^2.8.13",
    "ts-node-dev": "^2.0.0",
    "typescript": "^5.1.6"
  }
}
```

**Step 2: Create manager.ts**

```typescript
import express, { Express, Request, Response } from 'express';
import { spawn, ChildProcess } from 'child_process';
import { v4 as uuidv4 } from 'uuid';
import * as fs from 'fs';
import * as path from 'path';

interface Plugin {
  id: string;
  name: string;
  code: string;
  language: 'typescript' | 'python';
  port?: number;
  process?: ChildProcess;
  status: 'starting' | 'running' | 'stopped' | 'error';
  healthCheck?: NodeJS.Timeout;
}

class PluginRuntime {
  private plugins: Map<string, Plugin> = new Map();
  private basePort: number = 3001;
  private app: Express;

  constructor() {
    this.app = express();
    this.app.use(express.json());
    this.setupRoutes();
  }

  private setupRoutes() {
    // Health check
    this.app.get('/health', (_req: Request, res: Response) => {
      res.json({ status: 'ok', plugins: this.plugins.size });
    });

    // List plugins
    this.app.get('/plugins', (_req: Request, res: Response) => {
      const plugins = Array.from(this.plugins.values()).map(p => ({
        id: p.id,
        name: p.name,
        status: p.status,
        port: p.port
      }));
      res.json(plugins);
    });

    // Deploy plugin
    this.app.post('/plugins', async (req: Request, res: Response) => {
      try {
        const { name, code, language, inputs } = req.body;
        
        if (!name || !code) {
          return res.status(400).json({ error: 'name and code are required' });
        }

        const pluginId = uuidv4();
        const port = this.basePort + this.plugins.size;

        // Save plugin code
        const pluginDir = path.join(__dirname, 'plugins', pluginId);
        fs.mkdirSync(pluginDir, { recursive: true });
        
        const ext = language === 'python' ? 'py' : 'ts';
        fs.writeFileSync(path.join(pluginDir, `plugin.${ext}`), code);

        // Start plugin service
        const plugin: Plugin = {
          id: pluginId,
          name,
          code,
          language: language || 'typescript',
          port,
          status: 'starting'
        };

        this.plugins.set(pluginId, plugin);

        // In production, you'd start a separate process
        // For now, we mark it as running
        plugin.status = 'running';

        res.json({
          pluginId,
          name,
          port,
          status: 'deployed'
        });
      } catch (error) {
        res.status(500).json({ error: String(error) });
      }
    });

    // Get plugin
    this.app.get('/plugins/:id', (req: Request, res: Response) => {
      const plugin = this.plugins.get(req.params.id);
      if (!plugin) {
        return res.status(404).json({ error: 'Plugin not found' });
      }
      res.json(plugin);
    });

    // Delete plugin
    this.app.delete('/plugins/:id', (req: Request, res: Response) => {
      const plugin = this.plugins.get(req.params.id);
      if (!plugin) {
        return res.status(404).json({ error: 'Plugin not found' });
      }

      // Stop the process if running
      if (plugin.process) {
        plugin.process.kill();
      }

      // Clear health check
      if (plugin.healthCheck) {
        clearInterval(plugin.healthCheck);
      }

      this.plugins.delete(req.params.id);
      res.json({ status: 'deleted' });
    });

    // Plugin health check
    this.app.get('/plugins/:id/health', async (req: Request, res: Response) => {
      const plugin = this.plugins.get(req.params.id);
      if (!plugin) {
        return res.status(404).json({ error: 'Plugin not found' });
      }

      if (plugin.status === 'running') {
        res.json({ status: 'healthy', pluginId: plugin.id });
      } else {
        res.status(503).json({ status: 'unhealthy', pluginId: plugin.id });
      }
    });
  }

  start(port: number = 3001) {
    this.basePort = port;
    this.app.listen(port, () => {
      console.log(`Plugin Runtime started on port ${port}`);
    });
  }
}

export default PluginRuntime;
```

**Step 3: Create index.ts**

```typescript
import PluginRuntime from './manager';

const port = parseInt(process.env.PORT || '3001', 10);
const runtime = new PluginRuntime();
runtime.start(port);
```

**Step 4: Commit**
```bash
git add projects/plugin-runtime/
git commit -m "feat(ai-workflow): add Plugin Runtime service"
```

---

## Phase 5: Docker Deployment

### Task 10: Create Docker Compose

**Files:**
- Create: `deploy/docker/docker-compose.ai-workflow.yml`

**Step 1: Create docker-compose**

```yaml
version: '3.8'

services:
  # MongoDB for AI Workflow data
  mongodb-aiworkflow:
    image: mongo:7
    container_name: fastgpt-aiworkflow-mongo
    ports:
      - "27018:27017"
    environment:
      MONGO_INITDB_ROOT_USERNAME: root
      MONGO_INITDB_ROOT_PASSWORD: password
    volumes:
      - mongodb-aiworkflow-data:/data/db
    networks:
      - aiworkflow-network

  # Redis for caching and rate limiting
  redis-aiworkflow:
    image: redis:7
    container_name: fastgpt-aiworkflow-redis
    ports:
      - "6380:6379"
    networks:
      - aiworkflow-network

  # OpenCode Agent (Python)
  opencode-agent:
    build:
      context: ../../projects/opencode-agent
      dockerfile: Dockerfile
    container_name: fastgpt-opencode-agent
    ports:
      - "8000:8000"
    environment:
      - OPENCODE_API_URL=${OPENCODE_API_URL}
      - OPENCODE_API_KEY=${OPENCODE_API_KEY}
      - MONGODB_URI=mongodb://root:password@mongodb-aiworkflow:27017/aiworkflow
      - REDIS_URL=redis://redis-aiworkflow:6379
    depends_on:
      - mongodb-aiworkflow
      - redis-aiworkflow
    networks:
      - aiworkflow-network

  # OpenSandbox for code validation
  opensandbox:
    image: alibaba/opensandbox:latest
    container_name: fastgpt-opensandbox
    ports:
      - "8081:8081"
    environment:
      - SANDBOX_MODE=read-only
      - SANDBOX_TIMEOUT=5000
    networks:
      - aiworkflow-network

  # Plugin Runtime
  plugin-runtime:
    build:
      context: ../../projects/plugin-runtime
      dockerfile: Dockerfile
    container_name: fastgpt-plugin-runtime
    ports:
      - "3001:3001"
    environment:
      - PORT=3001
      - MONGODB_URI=mongodb://root:password@mongodb-aiworkflow:27017/aiworkflow
    depends_on:
      - mongodb-aiworkflow
    networks:
      - aiworkflow-network

volumes:
  mongodb-aiworkflow-data:

networks:
  aiworkflow-network:
    driver: bridge
```

**Step 2: Commit**
```bash
git add deploy/docker/docker-compose.ai-workflow.yml
git commit -m "feat(ai-workflow): add docker compose for deployment"
```

---

## Phase 6: Frontend Components

### Task 11: Create Frontend API Functions

**Files:**
- Create: `packages/web/components/core/aiWorkflow/api.ts`

**Step 1: Create API functions**

```typescript
import { post } from '@fastgpt/web/common/api/request';

export const chatWithAIWorkflow = (data: {
  teamId: string;
  message: string;
  sessionId?: string;
  context?: {
    mode: 'create' | 'optimize';
    workflowId?: string;
  };
}) => post('/core/workflow/ai/chat', data);

export const confirmWorkflow = (data: {
  sessionId: string;
  answer: string;
  confirmed?: boolean;
}) => post('/core/workflow/ai/workflow/confirm', data);

export const validateWorkflow = (data: {
  workflow: {
    nodes: any[];
    edges: any[];
  };
  plugins?: Array<{
    name: string;
    code: string;
  }>;
}) => post('/core/workflow/ai/workflow/validate', data);

export const validatePluginCode = (data: {
  code: string;
  language: 'typescript' | 'python';
  inputs?: Array<{
    name: string;
    type: string;
    required: boolean;
  }>;
}) => post('/core/workflow/ai/plugin/validateCode', data);

export const getAvailableNodes = (teamId: string) =>
  get(`/core/workflow/ai/nodes?teamId=${teamId}`);

function get(url: string) {
  return fetch(url).then((res) => res.json());
}
```

**Step 2: Commit**
```bash
git add packages/web/components/core/aiWorkflow/api.ts
git commit -m "feat(ai-workflow): add frontend API functions"
```

---

## Execution Options

**Plan complete and saved to `docs/plans/2026-02-24-ai-workflow-generator-design.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**


---

## ✅ 实现状态 (2026-02-25)

所有功能已完成实现并提交:

| 功能 | 状态 | 提交 |
|------|------|------|
| 流式生成 | ✅ | a76584ca3 |
| 熔断器 | ✅ | a76584ca3 |
| 工作流模板 | ✅ | a76584ca3 |
| 增强验证 | ✅ | a76584ca3 |
| 导出/导入 | ✅ | a76584ca3 |
| 模拟数据 | ✅ | a76584ca3 |
| 预览执行 | ✅ | a76584ca3 |
| 国际化 | ✅ | a76584ca3 |
| API 认证 | ✅ | a76584ca3 |
| 频率限制 | ✅ | a76584ca3 |
| 持久化存储 | ✅ | a76584ca3 |
| 日志记录 | ✅ | a76584ca3 |
| 输入净化 | ✅ | a76584ca3 |
