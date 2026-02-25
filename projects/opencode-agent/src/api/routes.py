from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, AsyncGenerator
import os
import uuid
import json
import asyncio
import logging
import re
from datetime import datetime
from html import escape

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("opencode-agent")

# Input sanitization functions
def sanitize_input(text: str, max_length: int = 10000) -> str:
    """Sanitize user input to prevent XSS and injection attacks"""
    if not text:
        return ""
    # Limit length
    text = text[:max_length]
    # Escape HTML characters
    text = escape(text)
    return text

def sanitize_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize workflow nodes and edges"""
    if not workflow:
        return {}
    
    sanitized = {"nodes": [], "edges": []}
    
    # Sanitize nodes
    for node in workflow.get("nodes", []):
        if not isinstance(node, dict):
            continue
        sanitized_node = {
            "nodeId": re.sub(r'[^a-zA-Z0-9_-]', '', str(node.get("nodeId", "")))[:50],
            "flowNodeType": re.sub(r'[^a-zA-Z0-9_-]', '', str(node.get("flowNodeType", "")))[:50],
            "name": sanitize_input(str(node.get("name", ""))[:100]),
            "data": {},
        }
        sanitized["nodes"].append(sanitized_node)
    
    # Sanitize edges
    for edge in workflow.get("edges", []):
        if not isinstance(edge, dict):
            continue
        sanitized_edge = {
            "source": re.sub(r'[^a-zA-Z0-9_-]', '', str(edge.get("source", "")))[:50],
            "target": re.sub(r'[^a-zA-Z0-9_-]', '', str(edge.get("target", "")))[:50],
        }
        sanitized["edges"].append(sanitized_edge)
    
    return sanitized

# API version
API_VERSION = "v1"

# ============================================
# Authentication Configuration
# ============================================
# Get API keys from environment (comma-separated)
API_KEYS = set(os.environ.get("OPENCODE_API_KEYS", "").split(","))
API_KEYS.discard("")  # Remove empty string if present

def verify_api_key(api_key: str = None) -> bool:
    """Verify API key - returns True if valid or no keys configured (dev mode)"""
    if not API_KEYS:
        # No API keys configured - allow all (development mode)
        logger.warning("No API keys configured - running in development mode")
        return True
    
    if not api_key:
        return False
    
    return api_key in API_KEYS

# ============================================
# Rate Limiting Configuration
# ============================================
from collections import defaultdict
from time import time

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.max_requests = int(os.environ.get("RATE_LIMIT_MAX", "100"))
        self.window_seconds = int(os.environ.get("RATE_LIMIT_WINDOW", "60"))
    
    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed for identifier"""
        now = time()
        # Clean old requests
        self.requests[identifier] = [
            t for t in self.requests[identifier] 
            if now - t < self.window_seconds
        ]
        
        if len(self.requests[identifier]) >= self.max_requests:
            return False
        
        self.requests[identifier].append(now)
        return True
    
    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests for identifier"""
        now = time()
        current = [
            t for t in self.requests[identifier] 
            if now - t < self.window_seconds
        ]
        return max(0, self.max_requests - len(current))

rate_limiter = RateLimiter()

# ============================================
# Persistent Storage (SQLite)
# ============================================
import sqlite3
import threading

DB_PATH = os.environ.get("OPENCODE_DB_PATH", "/tmp/opencode_agent.db")
_db_lock = threading.Lock()

def init_db():
    """Initialize SQLite database"""
    with _db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                workflow TEXT NOT NULL,
                tags TEXT,
                is_public INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                usage_count INTEGER DEFAULT 0
            )
        """)
        
        # API usage log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT,
                endpoint TEXT,
                method TEXT,
                status_code INTEGER,
                timestamp TEXT NOT NULL,
                duration_ms INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {DB_PATH}")

# Initialize database on module load
try:
    init_db()
except Exception as e:
    logger.warning(f"Failed to initialize database: {e}")

def save_template_to_db(template: Dict[str, Any]) -> bool:
    """Save template to SQLite database"""
    try:
        with _db_lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO workflow_templates 
                (id, name, description, workflow, tags, is_public, created_at, updated_at, usage_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                template["id"],
                template["name"],
                template.get("description", ""),
                json.dumps(template["workflow"]),
                json.dumps(template.get("tags", [])),
                1 if template.get("is_public") else 0,
                template["created_at"],
                template["updated_at"],
                template.get("usage_count", 0)
            ))
            conn.commit()
            conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to save template: {e}")
        return False

def load_templates_from_db(tag: str = None, search: str = None, limit: int = 20) -> List[Dict]:
    """Load templates from SQLite database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM workflow_templates WHERE 1=1"
        params = []
        
        if tag:
            query += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')
        
        if search:
            query += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        
        query += " ORDER BY usage_count DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        templates = []
        for row in rows:
            templates.append({
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "workflow": json.loads(row["workflow"]),
                "tags": json.loads(row["tags"]),
                "is_public": bool(row["is_public"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "usage_count": row["usage_count"]
            })
        
        return templates
    except Exception as e:
        logger.error(f"Failed to load templates: {e}")
        return []

def get_template_from_db(template_id: str) -> Dict:
    """Get single template from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workflow_templates WHERE id = ?", (template_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "workflow": json.loads(row["workflow"]),
            "tags": json.loads(row["tags"]),
            "is_public": bool(row["is_public"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "usage_count": row["usage_count"]
        }
    except Exception as e:
        logger.error(f"Failed to get template: {e}")
        return None

def delete_template_from_db(template_id: str) -> bool:
    """Delete template from database"""
    try:
        with _db_lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM workflow_templates WHERE id = ?", (template_id,))
            conn.commit()
            affected = cursor.rowcount
            conn.close()
        return affected > 0
    except Exception as e:
        logger.error(f"Failed to delete template: {e}")
        return False

def increment_template_usage(template_id: str) -> bool:
    """Increment template usage count"""
    try:
        with _db_lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE workflow_templates SET usage_count = usage_count + 1 WHERE id = ?", (template_id,))
            conn.commit()
            conn.close()
        return True
    except Exception as e:
        logger.error(f"Failed to increment usage: {e}")
        return False

from datetime import datetime

WORKFLOW_SCHEMA_VERSION = "1.0.0"
GENERATOR_VERSION = "1.0.0"

def create_workflow_metadata():
    return {"schema_version": WORKFLOW_SCHEMA_VERSION, "generated_at": datetime.now().isoformat(), "generator_version": GENERATOR_VERSION}

def generate_trace_id():
    return f"wf-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:12]}"

I18N_MESSAGES = {"zh-CN": {"status.ready": "工作流已生成", "status.error": "生成失败", "error.generation_failed": "工作流生成失败"}, "en": {"status.ready": "Workflow generated", "status.error": "Generation failed", "error.generation_failed": "Workflow generation failed"}}
def get_i18n(key, lang="zh-CN"):
    return I18N_MESSAGES.get(lang, I18N_MESSAGES["zh-CN"]).get(key, key)

_workflow_templates: Dict[str, Dict[str, Any]] = {}

from ..agent.workflow_generator import WorkflowGenerator
from ..agent.intent_analyzer import IntentAnalyzer
from ..agent.variable_mapper import VariableMappingEngine, ConfidenceLevel
from ..agent.validation_engine import ValidationEngine, ValidationLevel
from ..agent.rag_knowledge_base import RAGKnowledgeBase, CaseStatus
from ..agent.state_machine import state_machine, GenerationState, ClarificationQuestion
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import uuid

from ..agent.workflow_generator import WorkflowGenerator
from ..agent.intent_analyzer import IntentAnalyzer
from ..agent.variable_mapper import VariableMappingEngine, ConfidenceLevel
from ..agent.validation_engine import ValidationEngine, ValidationLevel
from ..agent.rag_knowledge_base import RAGKnowledgeBase, CaseStatus
from ..agent.state_machine import state_machine, GenerationState, ClarificationQuestion


app = FastAPI(title="FastGPT AI Workflow Agent")

# Authentication dependency
from fastapi import Depends
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_current_user(api_key: str = Depends(api_key_header)):
    """Verify API key from header"""
    if not verify_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return {"api_key": api_key}

# Rate limiting dependency
async def check_rate_limit():
    """Check rate limit for request"""
    # Use API key as identifier if available, otherwise use IP
    identifier = "default"
    
    if not rate_limiter.is_allowed(identifier):
        raise HTTPException(
            status_code=429, 
            detail=f"Rate limit exceeded. Max {rate_limiter.max_requests} requests per {rate_limiter.window_seconds} seconds"
        )


class ChatRequest(BaseModel):
    team_id: str
    message: str
    session_id: Optional[str] = None


class GenerateRequest(BaseModel):
    userIntent: str
    sessionId: Optional[str] = None
    context: Optional[Dict[str, Any]] = {}
    options: Optional[Dict[str, Any]] = {}


class ConfirmRequest(BaseModel):
    sessionId: str
    answer: str
    context: Optional[Dict[str, Any]] = {}
    confirmed: Optional[bool] = False


class ChatResponse(BaseModel):
    session_id: str
    message: str
    workflow: Optional[dict] = None
    status: Optional[str] = None
    questions: Optional[List[Dict]] = None


fastgpt_client = None
agent = {}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    global agent
    if not agent.get("workflow_agent"):
        from ..tools.fastgpt import FastGPTClient
        from ..agent.core import WorkflowAgent

        fastgpt_base_url = os.environ.get("FASTGPT_API_URL", "http://fastgpt:3000")
        fastgpt_api_key = os.environ.get("FASTGPT_API_KEY", "")

        fastgpt_client = FastGPTClient(
            base_url=fastgpt_base_url, api_key=fastgpt_api_key
        )
        agent["workflow_agent"] = WorkflowAgent(fastgpt_client)

    result = await agent["workflow_agent"].chat(request.team_id, request.message)
    return ChatResponse(
        session_id=request.session_id or str(uuid.uuid4()),
        message=result.get("message", ""),
        workflow=result.get("workflow"),
    )


def extract_tool_context(context: Dict[str, Any]) -> Dict[str, Any]:
    available_plugins = context.get("availablePlugins", [])
    node_types = context.get("nodeTypes", [])
    categories = context.get("categories", [])

    if available_plugins and isinstance(available_plugins[0], str):
        available_plugins = [{"name": p} for p in available_plugins]

    return {
        "availablePlugins": available_plugins,
        "nodeTypes": node_types,
        "categories": categories,
    }


@app.post("/api/ai-workflow/generate")
async def generate_workflow(request: GenerateRequest, user: dict = Depends(get_current_user)):
    # Check rate limit
    await check_rate_limit()
    trace_id = generate_trace_id()
    logger.info(f"[{trace_id}] Starting workflow generation for intent: {request.userIntent[:50]}...")
    
    # Sanitize input
    sanitized_intent = sanitize_input(request.userIntent)
    if not agent.get("workflow_generator"):
        from ..tools.fastgpt import FastGPTClient

        fastgpt_base_url = os.environ.get("FASTGPT_API_URL", "http://fastgpt:3000")
        fastgpt_api_key = os.environ.get("FASTGPT_API_KEY", "")

        fastgpt_client = FastGPTClient(
            base_url=fastgpt_base_url, api_key=fastgpt_api_key
        )

        intent_analyzer = IntentAnalyzer()
        workflow_gen = WorkflowGenerator()
        variable_mapper = VariableMappingEngine()
        validation_engine = ValidationEngine()
        rag_kb = RAGKnowledgeBase()

        agent["client"] = fastgpt_client
        agent["intent_analyzer"] = intent_analyzer
        agent["workflow_generator"] = workflow_gen
        agent["variable_mapper"] = variable_mapper
        agent["validation_engine"] = validation_engine
        agent["rag_kb"] = rag_kb

    session_id = request.sessionId or str(uuid.uuid4())

    try:
        session = state_machine.create_session(session_id, request.userIntent)

        state_machine.start_generation(session_id)

        context = request.context or {}

        rag_context = await agent["rag_kb"].get_system_prompt_context(
            request.userIntent
        )

        enhanced_requirements = request.userIntent
        if rag_context:
            enhanced_requirements += f"\n\n{rag_context}"

        intent_result = await agent["intent_analyzer"].analyze(enhanced_requirements)

        tool_context = extract_tool_context(context)

        workflow_result = await agent["workflow_generator"].generate(
            intent=intent_result.intent.value,
            complexity=intent_result.complexity.value,
            requirements=enhanced_requirements,
            available_plugins=tool_context["availablePlugins"],
            node_types=tool_context["nodeTypes"],
            categories=tool_context["categories"],
        )

        if not workflow_result.is_valid:
            state_machine.error(session_id, "Workflow generation failed")
            return {
                "sessionId": session_id,
                "status": "error",
                "message": "工作流生成失败",
                "workflow": None,
            }

        nodes_data = [n.model_dump() for n in workflow_result.nodes]
        edges_data = [e.model_dump() for e in workflow_result.edges]

        state_machine.start_validation(session_id, nodes_data, edges_data)



        # Circuit breaker: max 3 auto-fix attempts
        MAX_RETRIES = 3
        auto_fix_attempts = 0
        last_error = None
        
        for attempt in range(MAX_RETRIES + 1):
            validation_result = await agent["validation_engine"].validate(nodes_data, edges_data)
            if len(validation_result.errors) == 0: break
            if attempt < MAX_RETRIES:
                auto_fix_attempts += 1
                last_error = validation_result.errors[0].message
                try:
                    fixed = await agent["workflow_generator"].fix_workflow(nodes_data, edges_data, validation_result.errors)
                    nodes_data = [n.model_dump() for n in fixed.nodes]
                    edges_data = [e.model_dump() for e in fixed.edges]
                except Exception as fix_err:
                    logger.warning(f"[{trace_id}] Auto-fix attempt {auto_fix_attempts} failed: {str(fix_err)}")
                    break

        # If validation still failed after retries, trigger human review
        if validation_result.errors and auto_fix_attempts >= MAX_RETRIES:
            state_machine.start_review(session_id, [{"message": f"自动修复失败 ({auto_fix_attempts}/{MAX_RETRIES}): {last_error}", "severity": "error"}], [], force_human_review=True)
            return {"sessionId": session_id, "status": "reviewing", "message": get_i18n("error.human_review_required"), "workflow": {"nodes": nodes_data, "edges": edges_data}, "trace_id": generate_trace_id()}

        mapping_result = await agent["variable_mapper"].map_variables(
            nodes_data, edges_data
        )

        low_conf_mappings = [
            {
                "source_node_id": m.source_node_id,
                "source_variable": m.source_variable,
                "target_node_id": m.target_node_id,
                "target_variable": m.target_variable,
                "confidence": m.confidence,
            }
            for m in mapping_result.mappings
            if m.confidence_level == ConfidenceLevel.MEDIUM
        ]

        if low_conf_mappings or validation_result.warnings:
            state_machine.start_review(
                session_id,
                [
                    {"message": i.message, "severity": i.severity.value}
                    for i in validation_result.issues
                ],
                low_conf_mappings,
            )

            return {
                "sessionId": session_id,
                "status": "reviewing",
                "message": "工作流已生成，需要确认以下内容",
                "workflow": {"nodes": nodes_data, "edges": edges_data},
                "validation_issues": [
                    {"message": i.message, "severity": i.severity.value}
                    for i in validation_result.issues
                ],
                "low_confidence_mappings": low_conf_mappings,
                "suggestions": None,
            }

        state_machine.complete(session_id)

        await agent["rag_kb"].store_case(
            intent=request.userIntent,
            nodes=nodes_data,
            edges=edges_data,
            key_prompts=enhanced_requirements[:500],
            version="v1",
            tags=[intent_result.intent.value, intent_result.complexity.value],
            status=CaseStatus.SUCCESS,
        )

        return {
            "sessionId": session_id,
            "status": "ready",
            "message": "工作流已生成",
            "workflow": {"nodes": nodes_data, "edges": edges_data},
            "questions": None,
            "suggestions": None,
        }

    except Exception as e:
        state_machine.error(session_id, str(e))
        return {
            "sessionId": session_id,
            "status": "error",
            "message": f"生成失败: {str(e)}",
            "workflow": None,
        }


@app.post("/api/ai-workflow/validate")
async def validate_workflow(request: ValidateRequest):
    if not agent.get("validation_engine"):
        agent["validation_engine"] = ValidationEngine()

    try:
        workflow = request.workflow or {}
        nodes = workflow.get("nodes", [])
        edges = workflow.get("edges", [])

        result = await agent["validation_engine"].validate(nodes, edges)

        return {
            "valid": result.is_valid,
            "errors": [
                {
                    "message": i.message,
                    "severity": i.severity.value,
                    "level": i.level.value,
                }
                for i in result.errors
            ],
            "warnings": [
                {
                    "message": i.message,
                    "severity": i.severity.value,
                    "level": i.level.value,
                }
                for i in result.warnings
            ],
            "passed_levels": [l.value for l in result.passed_levels],
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [{"message": str(e), "severity": "error", "level": "static"}],
            "warnings": [],
            "passed_levels": [],
        }


@app.post("/api/ai-workflow/map-variables")
async def map_variables(request: ValidateRequest):
    if not agent.get("variable_mapper"):
        agent["variable_mapper"] = VariableMappingEngine()

    try:
        workflow = request.workflow or {}
        nodes = workflow.get("nodes", [])
        edges = workflow.get("edges", [])

        result = await agent["variable_mapper"].map_variables(nodes, edges)

        return {
            "mappings": [
                {
                    "source_node_id": m.source_node_id,
                    "source_variable": m.source_variable,
                    "target_node_id": m.target_node_id,
                    "target_variable": m.target_variable,
                    "confidence": m.confidence,
                    "confidence_level": m.confidence_level.value,
                    "reason": m.reason,
                }
                for m in result.mappings
            ],
            "unmapped_inputs": result.unmapped_inputs,
            "unmapped_outputs": result.unmapped_outputs,
            "automated_mappings": [
                {"source": m.source_variable, "target": m.target_variable}
                for m in result.mappings
                if m.confidence_level == ConfidenceLevel.HIGH
            ],
            "confirm_mappings": [
                {
                    "source": m.source_variable,
                    "target": m.target_variable,
                    "confidence": m.confidence,
                }
                for m in result.mappings
                if m.confidence_level == ConfidenceLevel.MEDIUM
            ],
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/ai-workflow/state/{session_id}")
async def get_state(session_id: str):
    state = state_machine.get_state(session_id)
    if not state:
        return {"error": "Session not found"}

    return {
        "session_id": session_id,
        "state": state.state.value,
        "lock_info": state_machine.get_lock_info(session_id),
        "nodes": state.nodes,
        "edges": state.edges,
    }


@app.post("/api/ai-workflow/state/{session_id}/confirm-mappings")
async def confirm_mappings(session_id: str, mappings: List[Dict]):
    state = state_machine.get_state(session_id)
    if not state:
        return {"error": "Session not found"}

    for m in mappings:
        state.edges.append(
            {
                "source": m.get("source_node_id"),
                "sourceHandle": "out",
                "target": m.get("target_node_id"),
                "targetHandle": "in",
            }
        )

    state_machine.complete(session_id)

    return {"status": "completed", "session_id": session_id}


@app.post("/api/ai-workflow/feedback")
async def record_feedback(request: Dict):
    if not agent.get("rag_kb"):
        agent["rag_kb"] = RAGKnowledgeBase()

    case_id = request.get("case_id")
    was_modified = request.get("was_modified", False)
    error_log = request.get("error_log")

    if case_id:
        await agent["rag_kb"].record_feedback(case_id, was_modified, error_log)

    return {"status": "recorded"}


# SSE Event helper
def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def generate_events(request: GenerateRequest) -> AsyncGenerator[str, None]:
    """Generate SSE events for streaming workflow generation"""
    
    # Initialize agents if needed
    if not agent.get("workflow_generator"):
        from ..tools.fastgpt import FastGPTClient
        
        fastgpt_base_url = os.environ.get("FASTGPT_API_URL", "http://fastgpt:3000")
        fastgpt_api_key = os.environ.get("FASTGPT_API_KEY", "")
        
        fastgpt_client = FastGPTClient(base_url=fastgpt_base_url, api_key=fastgpt_api_key)
        
        intent_analyzer = IntentAnalyzer()
        workflow_gen = WorkflowGenerator()
        variable_mapper = VariableMappingEngine()
        validation_engine = ValidationEngine()
        rag_kb = RAGKnowledgeBase()
        
        agent["client"] = fastgpt_client
        agent["intent_analyzer"] = intent_analyzer
        agent["workflow_generator"] = workflow_gen
        agent["variable_mapper"] = variable_mapper
        agent["validation_engine"] = validation_engine
        agent["rag_kb"] = rag_kb
    
    session_id = request.sessionId or str(uuid.uuid4())
    
    try:
        # Create session
        state_machine.create_session(session_id, request.userIntent)
        state_machine.start_generation(session_id)
        
        # Step 1: Intent Detection
        yield sse_event("aiWorkflowIntent", {
            "intent": "analyzing",
            "progress": 5,
            "message": "正在分析用户意图..."
        })
        
        # RAG context
        context = request.context or {}
        rag_context = await agent["rag_kb"].get_system_prompt_context(request.userIntent)
        enhanced_requirements = request.userIntent
        if rag_context:
            enhanced_requirements += f"\n\n{rag_context}"
        
        # Intent analysis
        intent_result = await agent["intent_analyzer"].analyze(enhanced_requirements)
        
        yield sse_event("aiWorkflowIntent", {
            "intent": intent_result.intent.value,
            "complexity": intent_result.complexity.value,
            "progress": 10,
            "message": f"意图识别完成: {intent_result.intent.value}"
        })
        
        # Step 2: Generate nodes progressively
        tool_context = extract_tool_context(context)
        
        yield sse_event("aiWorkflowNodeGenerating", {
            "progress": 10,
            "message": "正在生成工作流节点...",
            "stage": "planning"
        })
        
        # Generate workflow
        workflow_result = await agent["workflow_generator"].generate(
            intent=intent_result.intent.value,
            complexity=intent_result.complexity.value,
            requirements=enhanced_requirements,
            available_plugins=tool_context["availablePlugins"],
            node_types=tool_context["nodeTypes"],
            categories=tool_context["categories"],
        )
        
        if not workflow_result.is_valid:
            yield sse_event("error", {
                "message": "工作流生成失败",
                "progress": 0
            })
            return
        
        nodes_data = [n.model_dump() for n in workflow_result.nodes]
        edges_data = [e.model_dump() for e in workflow_result.edges]
        
        # Stream each node
        total_nodes = len(nodes_data)
        for i, node in enumerate(nodes_data):
            progress = 10 + int((i / max(total_nodes, 1)) * 50)
            yield sse_event("aiWorkflowNodeGenerating", {
                "progress": progress,
                "currentNode": node.get("flowNodeType", "unknown"),
                "nodeId": node.get("id", ""),
                "message": f"正在生成节点 {i+1}/{total_nodes}"
            })
            
            # Small delay for UX (can be removed in production)
            await asyncio.sleep(0.1)
            
            partial_nodes = nodes_data[:i+1]
            yield sse_event("aiWorkflowNodeGenerated", {
                "node": node,
                "progress": progress + int(50 / max(total_nodes, 1)),
                "partialWorkflow": {
                    "nodes": partial_nodes,
                    "edges": edges_data
                },
                "completed": i == total_nodes - 1
            })
        
        # Stream edges
        for i, edge in enumerate(edges_data):
            yield sse_event("aiWorkflowEdgeCreated", {
                "edge": edge,
                "progress": 60 + int((i / max(len(edges_data), 1)) * 10)
            })
        
        # Step 3: Validation
        yield sse_event("aiWorkflowValidationStart", {
            "progress": 70,
            "levels": ["static", "security", "sandbox"],
            "message": "正在验证工作流..."
        })
        
        state_machine.start_validation(session_id, nodes_data, edges_data)
        
        validation_result = await agent["validation_engine"].validate(nodes_data, edges_data)
        
        for idx, level in enumerate(["static", "security", "sandbox"]):
            progress = 70 + int((idx / 3) * 15)
            yield sse_event("aiWorkflowValidationProgress", {
                "level": level,
                "progress": progress,
                "completed": idx == 2
            })
        
        # Step 4: Variable Mapping
        yield sse_event("aiWorkflowMappingProgress", {
            "progress": 85,
            "message": "正在映射变量..."
        })
        
        mapping_result = await agent["variable_mapper"].map_variables(nodes_data, edges_data)
        
        low_conf_mappings = [
            {
                "source_node_id": m.source_node_id,
                "source_variable": m.source_variable,
                "target_node_id": m.target_node_id,
                "target_variable": m.target_variable,
                "confidence": m.confidence,
            }
            for m in mapping_result.mappings
            if m.confidence_level == ConfidenceLevel.MEDIUM
        ]
        
        # Step 5: Complete
        if low_conf_mappings or validation_result.warnings:
            state_machine.start_review(
                session_id,
                [{"message": i.message, "severity": i.severity.value} for i in validation_result.issues],
                low_conf_mappings,
            )
            
            yield sse_event("aiWorkflowComplete", {
                "status": "reviewing",
                "progress": 100,
                "workflow": {"nodes": nodes_data, "edges": edges_data},
                "validation_issues": [
                    {"message": i.message, "severity": i.severity.value}
                    for i in validation_result.issues
                ],
                "low_confidence_mappings": low_conf_mappings,
                "message": "工作流已生成，需要确认以下内容"
            })
        else:
            state_machine.complete(session_id)
            
            # Store case
            await agent["rag_kb"].store_case(
                intent=request.userIntent,
                nodes=nodes_data,
                edges=edges_data,
                key_prompts=enhanced_requirements[:500],
                version="v1",
                tags=[intent_result.intent.value, intent_result.complexity.value],
                status=CaseStatus.SUCCESS,
            )
            
            yield sse_event("aiWorkflowComplete", {
                "status": "ready",
                "progress": 100,
                "workflow": {"nodes": nodes_data, "edges": edges_data},
                "validation_issues": [],
                "low_confidence_mappings": [],
                "message": "工作流已生成"
            })
            
    except Exception as e:
        state_machine.error(session_id, str(e))
        yield sse_event("error", {
            "message": f"生成失败: {str(e)}",
            "progress": 0
        })


@app.post("/api/ai-workflow/generate/stream")
async def generate_workflow_stream(request: GenerateRequest):
    """Streaming workflow generation endpoint"""
    return StreamingResponse(
        generate_events(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# Export/Import endpoints
class ExportRequest(BaseModel):
    workflow: Dict[str, Any]
    format: str = "json"

@app.post("/api/ai-workflow/export")
async def export_workflow(request: ExportRequest):
    data = {"version": WORKFLOW_SCHEMA_VERSION, "exported_at": datetime.now().isoformat(), "workflow": request.workflow, "metadata": create_workflow_metadata()}
    if request.format == "json": return {"format": "json", "content": json.dumps(data, indent=2), "filename": f"workflow-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"}
    if request.format == "yaml":
        try:
            import yaml
            return {"format": "yaml", "content": yaml.dump(data), "filename": f"workflow-{datetime.now().strftime('%Y%m%d-%H%M%S')}.yaml"}
        except ImportError: 
            logger.warning("YAML export attempted but pyyaml not installed")
            return {"valid": False, "error": "YAML requires pyyaml"}
        except Exception as e:
            logger.error(f"YAML export error: {str(e)}")
            return {"valid": False, "error": str(e)}
    return {"valid": False, "error": "Use json or yaml"}

class ImportRequest(BaseModel):
    content: str
    format: str = "json"

@app.post("/api/ai-workflow/import")
async def import_workflow(request: ImportRequest):
    try:
        data = json.loads(request.content) if request.format == "json" else __import__("yaml").safe_load(request.content)
        return {"valid": True, "workflow": data.get("workflow", data)}
    except Exception as e: return {"valid": False, "error": str(e)}

# Template endpoints
class SaveTemplateRequest(BaseModel):
    name: str
    description: str = ""
    workflow: Dict[str, Any]
    tags: List[str] = []

async def save_template(request: SaveTemplateRequest, user: dict = Depends(get_current_user)):
    tid = f"template-{uuid.uuid4().hex[:12]}"
    template = {"id": tid, "name": request.name, "description": request.description, "workflow": request.workflow, "tags": request.tags, "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat(), "usage_count": 0}
    
    # Save to database
    if save_template_to_db(template):
        return {"valid": True, "template_id": tid}
    else:
        return {"valid": False, "error": "Failed to save template"}


@app.get("/api/ai-workflow/templates")
async def list_templates(tag: str = None, search: str = None, limit: int = 20, user: dict = Depends(get_current_user)):
    templates = load_templates_from_db(tag=tag, search=search, limit=limit)
    return {"valid": True, "templates": templates, "total": len(templates)}


@app.get("/api/ai-workflow/templates/{template_id}")
async def get_template(template_id: str, user: dict = Depends(get_current_user)):
    t = get_template_from_db(template_id)
    if not t: return {"valid": False, "error": "Not found"}
    increment_template_usage(template_id)
    return {"valid": True, "template": t}


@app.delete("/api/ai-workflow/templates/{template_id}")
async def delete_template(template_id: str, user: dict = Depends(get_current_user)):
    if not delete_template_from_db(template_id): return {"valid": False, "error": "Not found"}
    return {"valid": True}

@app.get("/api/ai-workflow/templates")
async def list_templates(tag: str = None, search: str = None, limit: int = 20):
    templates = list(_workflow_templates.values())
    if tag: templates = [t for t in templates if tag in t.get("tags", [])]
    if search: templates = [t for t in templates if search.lower() in t.get("name", "").lower()]
    return {"valid": True, "templates": sorted(templates, key=lambda x: x.get("usage_count", 0), reverse=True)[:limit]}

@app.get("/api/ai-workflow/templates/{template_id}")
async def get_template(template_id: str):
    t = _workflow_templates.get(template_id)
    if not t: return {"valid": False, "error": "Not found"}
    t["usage_count"] = t.get("usage_count", 0) + 1
    return {"valid": True, "template": t}

@app.delete("/api/ai-workflow/templates/{template_id}")
async def delete_template(template_id: str):
    if template_id not in _workflow_templates: return {"valid": False, "error": "Not found"}
    del _workflow_templates[template_id]
    return {"valid": True}

# Mock data endpoint
class MockDataRequest(BaseModel):
    workflow: Dict[str, Any]
    custom_inputs: Dict[str, Any] = {}

@app.post("/api/ai-workflow/mock-data")
async def generate_mock_data(request: MockDataRequest):
    if not agent.get("validation_engine"): agent["validation_engine"] = ValidationEngine()
    try:
        nodes = request.workflow.get("nodes", [])
        mock_data = agent["validation_engine"].static_validator._generate_mock_data(nodes)
        return {"valid": True, "mock_data": {**mock_data, **request.custom_inputs}}
    except Exception as e: return {"valid": False, "error": str(e)}

# Workflow Execution Preview endpoint
class PreviewRequest(BaseModel):
    workflow: Dict[str, Any]
    inputs: Dict[str, Any] = {}
    max_steps: int = 20


@app.post("/api/ai-workflow/preview")
async def preview_workflow(request: PreviewRequest):
    """Preview workflow execution with mock data"""
    try:
        nodes = request.workflow.get("nodes", [])
        edges = request.workflow.get("edges", [])
        
        # Build node map for quick lookup
        node_map = {n.get("nodeId"): n for n in nodes}
        
        # Build execution order (topological sort)
        execution_order = _topological_sort(nodes, edges)
        
        # Simulate execution
        results = {}
        execution_trace = []
        
        for i, node_id in enumerate(execution_order):
            if i >= request.max_steps: break
            
            node = node_map.get(node_id)
            if not node: continue
            
            node_type = node.get("flowNodeType")
            node_name = node.get("name", node_id)
            
            # Get input from previous nodes or user input
            input_data = _get_node_input(node_id, edges, results, request.inputs)
            
            # Simulate node execution based on type
            output_data = _simulate_node(node_type, node, input_data, results)
            
            results[node_id] = output_data
            
            execution_trace.append({
                "step": i + 1,
                "node_id": node_id,
                "node_name": node_name,
                "node_type": node_type,
                "status": "completed",
                "input": input_data,
                "output": output_data,
            })
        
        return {
            "valid": True,
            "execution_order": execution_order,
            "results": results,
            "execution_trace": execution_trace,
            "total_steps": len(execution_trace),
            "metadata": create_workflow_metadata(),
        }
    except Exception as e:
        return {"valid": False, "error": str(e), "execution_trace": []}


def _topological_sort(nodes: List[Dict], edges: List[Dict]) -> List[str]:
    """Sort nodes in execution order"""
    node_ids = [n.get("nodeId") for n in nodes]
    
    # Build adjacency and in-degree
    adj = {nid: [] for nid in node_ids}
    in_degree = {nid: 0 for nid in node_ids}
    
    for e in edges:
        src, tgt = e.get("source"), e.get("target")
        if src in adj and tgt in adj:
            adj[src].append(tgt)
            in_degree[tgt] += 1
    
    # Kahn's algorithm
    queue = [n for n in node_ids if in_degree[n] == 0]
    result = []
    
    while queue:
        node = queue.pop(0)
        result.append(node)
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    # Add remaining nodes (cyclic - shouldn't happen with valid workflows)
    result.extend([n for n in node_ids if n not in result])
    
    return result


def _get_node_input(node_id: str, edges: List[Dict], results: Dict, user_inputs: Dict) -> Dict:
    """Get input data for a node from previous nodes or user inputs"""
    input_data = {}
    
    # Find incoming edges
    incoming = [e for e in edges if e.get("target") == node_id]
    
    for edge in incoming:
        source_id = edge.get("source")
        if source_id in results:
            input_data.update(results[source_id])
    
    # Merge with user inputs
    input_data.update(user_inputs.get(node_id, {}))
    
    return input_data


def _simulate_node(node_type: str, node: Dict, input_data: Dict, results: Dict) -> Dict:
    """Simulate node execution based on type"""
    node_id = node.get("nodeId")
    config = node.get("data", {})
    
    if node_type == "workflowStart":
        return {"userChatInput": input_data.get("userChatInput", "[User input]")}
    
    elif node_type == "chatNode":
        model = config.get("model", "gpt-3.5-turbo")
        prompt = config.get("prompt", "")
        return {
            "responseText": f"[Mock response from {model}]",
            "model": model,
            "prompt_used": prompt[:50] + "..." if len(prompt) > 50 else prompt
        }
    
    elif node_type == "datasetSearchNode":
        query = input_data.get("userChatInput", "")
        return {
            "quoteList": [
                {"content": f"Mock document about: {query}", "score": 0.95},
                {"content": f"Related information: {query}", "score": 0.87}
            ],
            "query": query
        }
    
    elif node_type == "answerNode":
        return {"answerText": input_data.get("responseText", "[Final answer]")}
    
    elif node_type == "httpRequest468":
        return {"response": {"status": 200, "data": "[Mock HTTP response]"}}
    
    elif node_type == "code":
        return {"output": "[Mock code execution result]"}
    
    elif node_type == "ifElseNode":
        condition = config.get("condition", "")
        return {"result": True, "condition": condition}
    
    else:
        return {"status": "simulated", "node_type": node_type}

