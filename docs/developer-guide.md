# AI Workflow Generator - Developer Guide

## Overview

AI Workflow Generator allows users to create FastGPT workflows through natural language conversations. The system uses LLM to analyze user intent and generate valid workflow configurations.

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
│  │  /api/chat      │  │  /api/workflow  │  │  /api/session │  │
│  └────────┬────────┘  └────────┬────────┘  └──────┬────────┘  │
└───────────┼────────────────────┼─────────────────┼────────────┘
            │                    │                  │
            ▼                    ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│               Python Agent Service (FastAPI)                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │ IntentAnalyzer  │  │ WorkflowGenerator│  │ ErrorHandler │  │
│  └─────────────────┘  └─────────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────────────┘
            │                    │
            ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MongoDB + FastGPT Runtime                    │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
projects/
└── opencode-agent/           # Python FastAPI service
    ├── src/
    │   ├── agent/
    │   │   ├── core.py          # Main workflow agent
    │   │   ├── intent_analyzer.py   # Intent detection
    │   │   ├── workflow_generator.py # Node generation
    │   │   └── error_handler.py     # User-friendly errors
    │   ├── api/
    │   │   └── routes.py        # FastAPI endpoints
    │   └── tools/
    │       ├── fastgpt.py       # FastGPT API client
    │       ├── storage.py        # MongoDB operations
    │       └── queue.py          # Task queue
    ├── tests/
    │   ├── test_intent_analyzer.py
    │   └── test_workflow_generator.py
    └── pyproject.toml

packages/service/core/workflow/ai/
├── sessionSchema.ts      # MongoDB session model
├── sessionController.ts  # Session CRUD operations
└── pluginSchema.ts      # Plugin configuration
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

### 2. Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_intent_analyzer.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### 3. Start Development Server

```bash
# Set environment variables
export FASTGPT_API_URL=http://localhost:3000
export FASTGPT_API_KEY=your-api-key
export MONGODB_URI=mongodb://localhost:27017

# Run FastAPI server
uvicorn src.api.routes:app --reload --port 8000
```

## Core Components

### 1. IntentAnalyzer (`src/agent/intent_analyzer.py`)

Analyzes user messages to determine workflow intent.

**Key Classes:**
```python
class IntentType(str, Enum):
    CREATE_WORKFLOW = "create_workflow"
    MODIFY_WORKFLOW = "modify_workflow"
    ASK_QUESTION = "ask_question"
    CLARIFY = "clarify"
    UNKNOWN = "unknown"

class ComplexityType(str, Enum):
    SIMPLE = "simple"    # 1-2 nodes
    MEDIUM = "medium"    # 3-4 nodes
    COMPLEX = "complex"  # 5+ nodes

class IntentAnalyzer:
    async def analyze(self, message: str) -> IntentResult:
        """Analyze user message and return intent + complexity"""
```

**Usage:**
```python
analyzer = IntentAnalyzer(base_url="http://localhost:3000", api_key="key")
result = await analyzer.analyze("create a chatbot for customer support")
print(result.intent)    # IntentType.CREATE_WORKFLOW
print(result.complexity)  # ComplexityType.SIMPLE
```

### 2. WorkflowGenerator (`src/agent/workflow_generator.py`)

Generates valid FastGPT workflow nodes from requirements.

**Key Classes:**
```python
class FlowNodeType(str, Enum):
    WORKFLOW_START = "workflowStart"
    CHAT_NODE = "chatNode"
    DATASET_SEARCH = "datasetSearchNode"
    ANSWER_NODE = "answerNode"
    # ... other node types

class WorkflowGenerator:
    async def generate(
        self, 
        intent: str, 
        complexity: str, 
        requirements: str
    ) -> WorkflowResult:
        """Generate workflow nodes and edges"""

    async def validate(
        self, 
        nodes: List[Dict], 
        edges: List[Dict]
    ) -> ValidationResult:
        """Validate workflow structure"""
```

**Usage:**
```python
generator = WorkflowGenerator()
result = await generator.generate(
    intent="create_workflow",
    complexity="medium",
    requirements="chatbot with knowledge base"
)

print(f"Nodes: {len(result.nodes)}")
print(f"Edges: {len(result.edges)}")
# Access nodes: result.nodes[0].nodeId, .flowNodeType, .position
```

**Generated Node Types by Complexity:**

| Complexity | Nodes Generated |
|------------|-----------------|
| Simple | workflowStart → chatNode → answerNode |
| Medium | workflowStart → datasetSearchNode → chatNode → answerNode |
| Complex | workflowStart → [optional: datasetSearch, ifElse, code, httpRequest] → chatNode → answerNode |

### 3. Error Handler (`src/agent/error_handler.py`)

Provides user-friendly error messages with suggestions.

**Key Classes:**
```python
class ErrorCategory(str, Enum):
    VALIDATION = "validation"
    LLM = "llm"
    WORKFLOW = "workflow"
    SESSION = "session"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    UNKNOWN = "unknown"

def format_error_response(error: Exception) -> Dict:
    """Convert exception to user-friendly response"""

def format_validation_response(errors: List[str]) -> Dict:
    """Format validation errors for API response"""
```

**Response Format:**
```json
{
  "category": "validation",
  "message": "Your workflow needs a starting point.",
  "technical": "workflow must have a workflowStart node",
  "suggestions": [
    "Add a 'Workflow Start' node as the entry point",
    "This is required for the workflow to run"
  ],
  "canRetry": true
}
```

## MongoDB Schema

### Session Schema (`packages/service/core/workflow/ai/sessionSchema.ts`)

```typescript
interface AiWorkflowSession {
  teamId: string;
  tmbId: string;
  sessionId: string;
  mode: 'create' | 'optimize' | 'extend';
  status: 'active' | 'completed' | 'cancelled';
  messages: ChatMessage[];
  generatedWorkflowId?: string;
  
  // Workflow state tracking
  workflowState: {
    nodes: WorkflowNode[];
    edges: WorkflowEdge[];
    intent: {
      type: 'create_workflow' | 'modify_workflow' | 'ask_question' | 'clarify' | 'unknown';
    };
    complexity: 'simple' | 'medium' | 'complex';
    requirements?: string;
    isValid: boolean;
    validationErrors: string[];
    version: number;
  };
  
  createdAt: Date;
  updatedAt: Date;
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

2. **Add node template** in `_create_node()`:
```python
name_map = {
    # ... existing
    FlowNodeType.NEW_NODE.value: "New Node Name",
}
```

3. **Add validation** if needed in `validate()`:
```python
if FlowNodeType.NEW_NODE.value not in node_types:
    warnings.append("Consider adding a New Node for better functionality")
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

## Common Issues

### 1. Import Errors

If you get import errors, ensure:
```bash
# Install package in development mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### 2. LLM API Errors

The IntentAnalyzer falls back to rule-based analysis if LLM fails. Check:
- `FASTGPT_API_URL` environment variable
- `FASTGPT_API_KEY` is valid
- Network connectivity

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
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pytest Documentation](https://docs.pytest.org/)

## Contact

For questions or contributions, please open an issue on GitHub.
