from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, AsyncGenerator
import os
import uuid
import json
import asyncio

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
async def generate_workflow(request: GenerateRequest):
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

        validation_result = await agent["validation_engine"].validate(
            nodes_data, edges_data
        )

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