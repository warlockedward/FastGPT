# AI Workflow Generator - Enterprise Architecture Design

**Date:** 2026-02-24
**Status:** Approved for Implementation

## 1. System Overview

### 1.1 Purpose
Build an AI-powered workflow generation system for FastGPT that enables:
- Non-technical users to create workflows via natural language
- Developers to extend FastGPT with custom plugins
- Enterprise-grade features: multi-round conversation, auto-validation, analytics

### 1.2 Target Users
- **Non-technical users**: Create workflows without coding
- **Developers**: Extend FastGPT with custom plugins

### 1.3 Success Criteria
- Enterprise grade with full features
- Multi-round conversation support
- Auto-validation and auto-fix
- Analytics, monitoring, A/B testing

---

## 2. Architecture

### 2.1 High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FastGPT Platform                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                     AI Workflow Gateway (API Layer)                     │    │
│  │                    (Next.js API Routes in projects/app)                  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                      │                                           │
│          ┌───────────────────────────┼───────────────────────────┐              │
│          ▼                           ▼                           ▼              │
│  ┌───────────────┐         ┌─────────────────┐         ┌────────────────┐       │
│  │  Workflow     │         │  Plugin         │         │  Session       │       │
│  │  Service      │         │  Service        │         │  Service       │       │
│  └───────────────┘         └─────────────────┘         └────────────────┘       │
│                                      │                                           │
└──────────────────────────────────────┼───────────────────────────────────────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          ▼                            ▼                            ▼
┌──────────────────┐      ┌─────────────────────┐      ┌──────────────────┐
│  OpenCode API    │      │  OpenSandbox         │      │  MongoDB/Redis   │
│  (External)      │      │  (Code Validation)   │      │  (Data Store)    │
└──────────────────┘      └─────────────────────┘      └──────────────────┘
```

### 2.2 Microservices

| Service | Technology | Port | Responsibility |
|---------|------------|------|----------------|
| **AI Workflow Gateway** | Next.js API | 3000 | User API entry, auth, rate limiting |
| **Plugin Runtime** | Node.js/Express | 3001-3NNN | Dynamic plugin API hosting |
| **OpenCode Agent** | Python FastAPI | 8000 | AI brain for workflow generation |
| **OpenSandbox** | Java | 8081 | Code execution/validation |

---

## 3. Components

### 3.1 AI Workflow Gateway (Next.js)

**Location:** `projects/app/src/pages/api/core/workflow/ai/`

**API Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/core/workflow/ai/chat` | Main AI对话 |
| POST | `/api/core/workflow/ai/workflow/confirm` | Confirm/回答问题 |
| POST | `/api/core/workflow/ai/workflow/validate` | Validate workflow |
| POST | `/api/core/workflow/ai/workflow/create` | Create workflow |
| POST | `/api/core/workflow/ai/plugin` | Create plugin |
| POST | `/api/core/workflow/ai/plugin/:id/deploy` | Deploy plugin |
| GET | `/api/core/workflow/ai/plugin` | List plugins |
| GET | `/api/core/workflow/ai/analytics` | Usage analytics |

### 3.2 Plugin Runtime (Node.js/Express)

**Location:** `projects/plugin-runtime/`

**Architecture:**
```
┌─────────────────────────────────────────────────────────┐
│                  Plugin Runtime Manager                  │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Registry   │  │  Deployer   │  │  Monitor    │    │
│  │  - plugins │  │  - start    │  │  - health   │    │
│  │  - versions│  │  - stop     │  │  - metrics  │    │
│  │             │  │  - scale    │  │  - logs     │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### 3.3 OpenCode Agent (Python)

**Location:** `projects/opencode-agent/`

**Architecture:**
```
┌─────────────────────────────────────────┐
│           WorkflowAgent                  │
├─────────────────────────────────────────┤
│  - intent_analyzer: Parse user intent   │
│  - workflow_generator: Generate JSON    │
│  - plugin_generator: Create plugin code  │
│  - error_handler: Auto-fix failures     │
└─────────────────────────────────────────┘
```

---

## 4. Data Models

### 4.1 Session Schema

```typescript
{
  _id: ObjectId,
  sessionId: string,
  teamId: string,
  messages: [{
    role: 'user' | 'assistant',
    content: string,
    timestamp: Date
  }],
  context: {
    mode: 'create' | 'optimize',
    workflowId?: string,
    questions?: Question[]
  },
  status: 'active' | 'completed' | 'expired'
}
```

### 4.2 Plugin Schema

```typescript
{
  _id: ObjectId,
  pluginId: string,
  teamId: string,
  name: string,
  description: string,
  code: string,
  language: 'typescript' | 'python',
  inputs: [{ name, type, required }],
  outputs: [{ name, type }],
  version: string,
  status: 'draft' | 'deployed' | 'failed',
  runtimePort?: number,
  createdAt: Date,
  updatedAt: Date
}
```

---

## 5. Data Flows

### 5.1 Create New Workflow

1. User sends message to /chat
2. Gateway stores message in Session
3. Gateway calls OpenCode API
4. OpenCode returns workflow or questions
5. Return to user for confirmation
6. User confirms → /create → save workflow

### 5.2 Deploy Plugin

1. OpenCode generates plugin code
2. User clicks "Deploy"
3. Gateway validates via OpenSandbox
4. If valid: Deploy to Plugin Runtime
5. Return port to Gateway

---

## 6. Error Handling

| Error Type | Handling |
|------------|----------|
| OpenCode API failure | Retry 3x with exponential backoff |
| OpenSandbox timeout | Return pending, allow manual retry |
| Plugin crash | Auto-restart, notify after 3 failures |
| Invalid workflow | Return specific errors, suggest fixes |
| Rate limit | Queue request, notify wait time |

---

## 7. Security

- **API Authentication**: Team-based auth (existing FastGPT auth)
- **Plugin Sandboxing**: Isolated processes, resource limits
- **Code Execution**: Only via OpenSandbox (read-only, timeout)
- **Rate Limiting**: Per-team quota in Redis

---

## 8. Testing Strategy

| Layer | Testing |
|-------|---------|
| Unit | Jest for TypeScript, Pytest for Python |
| Integration | API tests with mocked OpenCode |
| E2E | Playwright for critical flows |
| Load | k6 for API stress testing |

---

## 9. Deployment

### Docker Compose

```yaml
services:
  gateway:
    build: ./projects/app
    ports:
      - "3000:3000"
  
  plugin-runtime:
    build: ./projects/plugin-runtime
    ports:
      - "3001:3001"
  
  opencode-agent:
    build: ./projects/opencode-agent
    ports:
      - "8000:8000"
  
  opensandbox:
    image: alibaba/opensandbox
    ports:
      - "8081:8081"
  
  mongodb:
    image: mongo:7
    ports:
      - "27017:27017"
  
  redis:
    image: redis:7
    ports:
      - "6379:6379"
```

---

## 10. Implementation Phases

### Phase 1: Foundation
- API Gateway implementation
- Session management
- Basic OpenCode integration

### Phase 2: Core Features
- Workflow generation
- Multi-round conversation
- Plugin management

### Phase 3: Runtime
- Plugin Runtime service
- Dynamic deployment
- Health monitoring

### Phase 4: Enterprise
- Analytics dashboard
- A/B testing
- Advanced monitoring



---

## 11. Gap Analysis & Improvements

### 11.1 Five Key Gaps Identified

| # | Gap | Current State | Proposed Solution |
|---|-----|---------------|-------------------|
| 1 | **Streaming Generation** | Serial execution, 10-30s wait | SSE for node-by-node streaming |
| 2 | **Self-Healing Retry Policy** | Unlimited retries | Circuit breaker: max 3 auto-fixes, then human review |
| 3 | **Mock Data Generation** | LLM generates complex logic | Schema-based random fill + key field constraints |
| 4 | **Schema Version Management** | No version control | Workflow JSON carries `schema_version` field |
| 5 | **Observability** | No trace ID | OpenTelemetry + `trace_id` for session tracking |

#### Gap 1: Streaming Generation

**Problem:** Full workflow generation involves: intent recognition → planning → mapping → validation → fix. Serial execution forces users to wait 10-30 seconds.

**Missing:** No streaming generation design.

**Improvement:** Design "node-by-node generation and rendering". When LLM plans one node, frontend renders one node immediately instead of waiting for all.

**Implementation:**
- Backend: `/api/core/workflow/ai/chat` returns `text/event-stream`
- Event types: `node_generated`, `validation_progress`, `error`, `complete`
- Frontend: EventSource/SSE client accumulates nodes progressively

#### Gap 2: Self-Healing Retry Policy

**Problem:** Documentation mentions "validation failure triggers auto-fix" but lacks context management.

**Missing:** If LLM fails 3 consecutive fixes, what should system do? Unlimited retries waste tokens and frustrate users.

**Improvement:** Design "circuit breaker retry strategy":
- Max 3 auto-fix attempts per error
- After 3 failures: lock error node, generate human-readable error report
- Guide user to manual fix instead of blind machine guessing

#### Gap 3: Dynamic Mock Data Generation

**Problem:** Previously mentioned "dynamically return mock data based on branch logic". Requires LLM to understand branch conditions (e.g., `if score > 80`) and generate data meeting those conditions.

**Missing:** This is an independent difficulty - equivalent to having LLM write test cases. Wrong mock data causes false validation failures.

**Improvement:** Simplify mock data generation to "schema-based random filling":
- Only apply logic constraints on key fields
- Instead of LLM generating complex logic data
- Or provide "manual mock data injection" entry point

#### Gap 4: Schema Version Compatibility

**Problem:** Rely on OpenCode Agent to fetch Schema in real-time. If FastGPT updates at night, daytime cache may become invalid.

**Missing:** No schema version management.

**Improvement:** Generated workflow JSON should carry `schema_version` field:
- Validation engine must support multi-version schema compatibility
- If version mismatch detected, force cache refresh and notify user

#### Gap 5: Observability (Tracing)

**Problem:** Decision chain recording mentioned but no Trace ID defined.

**Missing:** When user reports "generation is wrong", how does dev team quickly locate which LLM call, which RAG retrieval caused the issue?

**Improvement:** Introduce distributed tracing (e.g., OpenTelemetry):
- Generate unique `trace_id` for each generation session
- Chain LLM input/output, RAG retrieval content, validation logs

---

## 12. Second Delivery Improvements

If this were a second delivery, I would shift from "Architecture Design Document" to "Executable Engineering Blueprint". Focus on:

### 12.1 From "Document" to "Skeleton Code"

Not just describing "need a variable mapping engine" but providing direct TypeScript interface definitions and pseudo-code implementations.

### 12.2 Add Decision Trees & Flow Diagrams

Text description不如清晰的时序图。

### 12.3 Provide Acceptance Test Suite

Not just "10 test cases" but specific input/output expectations for each.

| Case ID | Input | Expected Output | Validation |
|---------|-------|-----------------|------------|
| Case_01 | "翻译机器人" | 3 nodes, no branches | Nodes = 3, Edges = 2 |
| Case_02 | "情感分析" | 1 conditional branch, 2 paths | Branch node exists |
| Case_03 | [Type error] | Validation error | Error contains "type mismatch" |
| Case_04 | "天气查询" | Tool: weather-api | Tool node found |
| Case_05 | "循环工作流" | Loop detected | Error or warning |

### 12.4 Add Risk Register

Clearly list known risks, probability, impact, and mitigation.

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Embedding model OOM | Medium | High | API fallback mode |
| User generates infinite loop | Low | High | Sandbox hard limit on max steps |
| Schema version mismatch | Medium | Medium | Auto-refresh cache |
| vLLM service down | Low | High | Retry with exponential backoff |

---

## 13. Implementation Priority

Recommended order for addressing gaps:

1. **High Impact, Low Effort**
   - Gap 4: Schema version field (1 day)
   - Gap 5: Trace ID basic implementation (1 day)

2. **High Impact, Medium Effort**
   - Gap 1: Streaming generation (3-5 days)
   - Gap 2: Circuit breaker retry (2-3 days)

3. **Medium Impact, High Effort**
   - Gap 3: Mock data simplification (5-7 days)

---

## 14. Next Steps

1. Review and approve this gap analysis
2. Select priority items for implementation
3. Create detailed technical specs for each selected item
4. Assign to team members

---

**Document Version:** 1.1  
**Last Updated:** 2026-02-25  
**Author:** Sisyphus (AI Agent)  
**Status:** Gap Analysis Complete - Ready for Discussion