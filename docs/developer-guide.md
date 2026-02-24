# AI Workflow Generator - Developer Guide

## Overview

AI Workflow Generator allows users to create FastGPT workflows through natural language conversations. The system uses vLLM (local LLM) to analyze user intent and generate valid workflow configurations.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │  Chat UI        │  │  Workflow Preview │  │  Template Lib │  │
│  └────────┬────────┘  └────────┬────────┘  └──────┬────────┘  │
└───────────┼────────────────────┼─────────────────┼────────────┘
            │                    │                  │
            ▼                    ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Layer (Next.js)                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │  /api/chat      │  │  /api/workflow  │  │  /api/nodes  │  │
│  └────────┬────────┘  └────────┬────────┘  └──────┬────────┘  │
└───────────┼────────────────────┼─────────────────┼────────────┘
            │                    │                  │
            ▼                    ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│               Python Agent Service (FastAPI)                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │ IntentAnalyzer  │  │WorkflowGenerator│  │ ErrorHandler │  │
│  └─────────────────┘  └─────────────────┘  └───────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    vLLM (LLM Brain)                         │  │
│  │         http://165.154.97.202:38004                       │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
projects/
└── opencode-agent/           # Python FastAPI service
    ├── src/
    │   ├── agent/
    │   │   ├── core.py              # Main workflow agent
    │   │   ├── intent_analyzer.py   # Intent detection (v2.0 complexity)
    │   │   ├── workflow_generator.py # Node generation (LLM + fallback)
    │   │   └── error_handler.py     # User-friendly errors
    │   ├── api/
    │   │   └── routes.py            # FastAPI endpoints
    │   └── tools/
    │       ├── fastgpt.py          # FastGPT API client
    │       ├── storage.py          # MongoDB operations
    │       └── queue.py            # Task queue
    ├── tests/
    │   ├── test_intent_analyzer.py
    │   └── test_workflow_generator.py
    └── pyproject.toml

projects/app/src/pages/api/core/workflow/ai/
├── chat.ts                  # AI chat endpoint (passes full tool data)
├── nodes.ts                # Get available nodes with full details
└── workflow/
    ├── create.ts           # Create workflow
    ├── confirm.ts          # Confirm/answer
    └── validate.ts         # Validate workflow
```

## Quick Start

### 1. Setup Python Environment

```bash
cd projects/opencode-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -e .
pip install pytest pytest-asyncio httpx pydantic
```

### 2. Configure Environment Variables

```bash
# vLLM Configuration (LLM Brain)
export VLLM_BASE_URL=http://165.154.97.202:38004
export VLLM_MODEL=Qwen3-235B-A22B-Thinking-2507
export VLLM_API_KEY=your-api-key

# FastGPT Configuration
export FASTGPT_API_URL=http://localhost:3000
export FASTGPT_API_KEY=your-fastgpt-api-key
```

### 3. Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_intent_analyzer.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### 4. Start Development Server

```bash
# Run FastAPI server
uvicorn src.api.routes:app --reload --port 8000
```

## Data Flow

### Full Tool Data Pipeline

1. **User Input** → Frontend sends natural language description

2. **FastGPT Backend** (`chat.ts`)
   - Calls `/api/core/workflow/ai/nodes` to get full tool details
   - Extracts: tools (inputs, outputs, tags), nodeTypes, categories
   - Sends to Python Agent with full context

3. **Python Agent** (`routes.py`)
   - `extract_tool_context()`: Extracts availablePlugins, nodeTypes, categories
   - Passes to `WorkflowGenerator.generate()`

4. **WorkflowGenerator** (`workflow_generator.py`)
   - `_build_system_prompt()`: Creates prompt with all tool/node info
   - `_call_llm()`: Calls vLLM API for generation
   - `_parse_llm_response()`: Parses JSON response
   - Falls back to rule-based generation if LLM fails

5. **Return** workflow to frontend

## Core Components

### 1. IntentAnalyzer (`src/agent/intent_analyzer.py`)

Analyzes user messages to determine workflow intent using complexity analysis v2.0.

**Key Classes:**
```python
class IntentType(str, Enum):
    CREATE_WORKFLOW = "create_workflow"
    MODIFY_WORKFLOW = "modify_workflow"
    ASK_QUESTION = "ask_question"
    CLARIFY = "clarify"
    UNKNOWN = "unknown"

class ComplexityType(str, Enum):
    SIMPLE = "simple"     # Linear flow, no conditions
    MEDIUM = "medium"    # 1-2 conditions or dependencies
    COMPLEX = "complex"  # 3+ conditions + external integration

class IntentAnalyzer:
    async def analyze(self, message: str) -> IntentResult:
        """Analyze user message and return intent + complexity"""
```

**Usage:**
```python
analyzer = IntentAnalyzer(
    base_url="http://localhost:38004",
    api_key="key",
    model="Qwen3-235B-A22B-Thinking-2507"
)
result = await analyzer.analyze("create a chatbot for customer support")
print(result.intent)      # IntentType.CREATE_WORKFLOW
print(result.complexity)  # ComplexityType.SIMPLE
```

### 2. WorkflowGenerator (`src/agent/workflow_generator.py`)

Generates valid FastGPT workflow nodes using LLM with fallback to rules.

**Key Classes:**
```python
class FlowNodeType(str, Enum):
    WORKFLOW_START = "workflowStart"
    CHAT_NODE = "chatNode"
    DATASET_SEARCH = "datasetSearchNode"
    ANSWER_NODE = "answerNode"
    IF_ELSE = "ifElseNode"
    HTTP_REQUEST = "httpRequest468"
    CODE = "code"
    # ... other node types

class WorkflowGenerator:
    def __init__(self, base_url=None, api_key=None, model=None):
        # Uses VLLM_BASE_URL, VLLM_MODEL env vars

    async def generate(
        self, 
        intent: str, 
        complexity: str, 
        requirements: str,
        available_plugins: List[Dict] = None,
        node_types: List[Dict] = None,
        categories: List[Dict] = None
    ) -> WorkflowResult:
        """Generate workflow using LLM with rule-based fallback"""

    async def validate(
        self, 
        nodes: List[Dict], 
        edges: List[Dict]
    ) -> ValidationResult:
        """Validate workflow structure"""
```

**Usage:**
```python
generator = WorkflowGenerator(
    base_url="http://165.154.97.202:38004",
    model="Qwen3-235B-A22B-Thinking-2507"
)
result = await generator.generate(
    intent="create_workflow",
    complexity="medium",
    requirements="chatbot with knowledge base",
    available_plugins=[{"name": "weather", "description": "Get weather", "flowNodeType": "tool"}],
    node_types=[{"id": "chatNode", "label": "AI 对话", "category": "ai"}],
    categories=[{"id": "ai", "label": "AI 节点"}]
)

print(f"Nodes: {len(result.nodes)}")
print(f"Edges: {len(result.edges)}")
# Access: result.nodes[0].nodeId, .flowNodeType, .position
```

**Generated Node Types by Complexity:**

| Complexity | Nodes Generated |
|------------|-----------------|
| Simple | workflowStart → chatNode → answerNode |
| Medium | workflowStart → datasetSearchNode → chatNode → answerNode |
| Complex | workflowStart → [optional: datasetSearch, ifElse, code, httpRequest] → chatNode → answerNode |

### 3. Error Handler (`src/agent/error_handler.py`)

Provides user-friendly error messages with suggestions.

**Response Format:**
```json
{
  "category": "validation",
  "message": "Your workflow needs a starting point.",
  "technical": "workflow must have a workflowStart node",
  "suggestions": [
    "Add a 'Workflow Start' node as the entry point"
  ],
  "canRetry": true
}
```

## API Endpoints

### Chat Endpoint

**POST** `/api/core/workflow/ai/chat`

Request:
```json
{
  "message": "create a chatbot for customer support",
  "sessionId": "optional-session-id",
  "mode": "create"
}
```

Response:
```json
{
  "message": "Generated a simple workflow with 3 nodes...",
  "sessionId": "new-session-id",
  "workflow": {
    "nodes": [...],
    "edges": [...]
  }
}
```

### Nodes Endpoint (Extended)

**GET** `/api/core/workflow/ai/nodes?teamId=xxx`

Returns full tool and node type information:

```json
{
  "tools": [
    {
      "id": "tool_xxx",
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
    }
  ],
  "categories": [
    {"id": "core", "label": "核心节点"},
    {"id": "ai", "label": "AI 节点"}
  ]
}
```

## Development Workflow

### 1. TDD Approach (Required)

Follow Test-Driven Development for all new features:

```bash
# RED - Write failing test first
python -m pytest tests/test_your_feature.py -v
# Should fail with: ModuleNotFoundError

# GREEN - Implement minimal code to pass test
# ... write implementation ...

# GREEN - Verify tests pass
python -m pytest tests/test_your_feature.py -v
# Should pass

# REFACTOR - Clean up if needed
```

### 2. Adding New Node Types

To add a new node type:

1. **Update FlowNodeType enum** in `workflow_generator.py`:
```python
class FlowNodeType(str, Enum):
    # ... existing types
    NEW_NODE = "newNodeType"
```

2. **Add node metadata** in `_build_node_type_metadata()`:
```python
"newNodeType": {"label": "新节点", "category": "custom", "description": "Description"}
```

3. **Add name mapping** in `_create_node()`:
```python
name_map = {
    # ... existing
    FlowNodeType.NEW_NODE.value: "New Node Name",
}
```

4. **Add tests:**
```python
async def test_generate_workflow_with_new_node(self):
    result = await generator.generate(
        intent="create_workflow",
        complexity="medium", 
        requirements="something requiring new node"
    )
    assert FlowNodeType.NEW_NODE.value in [n.flowNodeType for n in result.nodes]
```

### 3. Adding New Error Types

Add new error mappings in `error_handler.py`:

```python
ERROR_MAPPINGS = {
    # ... existing
    "your error pattern": UserFriendlyError(
        category=ErrorCategory.YOUR_CATEGORY,
        user_message="User-friendly message",
        suggestions=["Suggestion 1", "Suggestion 2"],
        can_retry=True
    ),
}
```

## Testing

### Unit Tests

Location: `projects/opencode-agent/tests/`

```bash
# Run all tests
python -m pytest tests/ -v

# Run with verbose output
python -m pytest tests/ -vv

# Run specific test
python -m pytest tests/test_intent_analyzer.py::TestIntentAnalyzer::test_name -v
```

### Integration Tests

```python
async def test_full_workflow():
    # 1. Analyze intent
    analyzer = IntentAnalyzer()
    intent = await analyzer.analyze("create a chatbot")
    
    # 2. Generate workflow
    generator = WorkflowGenerator()
    workflow = await generator.generate(
        intent.intent.value,
        intent.complexity.value,
        intent.requirements
    )
    
    # 3. Validate
    validation = await generator.validate(
        [n.model_dump() for n in workflow.nodes],
        [e.model_dump() for e in workflow.edges]
    )
    
    assert validation.is_valid
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VLLM_BASE_URL` | vLLM API address | `http://fastgpt:3000` |
| `VLLM_MODEL` | Model name | `Qwen3-235B-A22B-Thinking-2507` |
| `VLLM_API_KEY` | API key | - |
| `FASTGPT_API_URL` | FastGPT API address | `http://fastgpt:3000` |
| `FASTGPT_API_KEY` | FastGPT API key | - |

## Common Issues

### 1. Import Errors

If you get import errors, ensure:
```bash
# Install package in development mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### 2. vLLM Connection Errors

Check:
- `VLLM_BASE_URL` is correct and accessible
- `VLLM_MODEL` is available on the server
- Network connectivity to vLLM server

The system will fall back to rule-based generation if LLM fails.

### 3. Validation Failures

Common validation errors:
- Missing `workflowStart` node
- Missing `answerNode` as final output
- Orphan nodes (not connected)
- Invalid edge references

## Code Style

- Use **Pydantic** for data validation
- Use **httpx.AsyncClient** for HTTP calls
- Use **pytest-asyncio** for async tests
- Follow **PEP 8** for Python code
- Use **type hints** everywhere possible

## Resources

- [FastGPT Workflow Documentation](https://docs.fastgpt.ai/)
- [vLLM Documentation](https://docs.vllm.ai/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pytest Documentation](https://docs.pytest.org/)

## Contact

For questions or contributions, please open an issue on GitHub.
