from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import uuid


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


class ChatResponse(BaseModel):
    session_id: str
    message: str
    workflow: Optional[dict] = None
    status: Optional[str] = None
    questions: Optional[List[Dict]] = None


fastgpt_client = None
agent = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    global agent
    if agent is None:
        from ..tools.fastgpt import FastGPTClient
        from ..agent.core import WorkflowAgent
        
        fastgpt_base_url = os.environ.get("FASTGPT_API_URL", "http://fastgpt:3000")
        fastgpt_api_key = os.environ.get("FASTGPT_API_KEY", "")
        
        fastgpt_client = FastGPTClient(
            base_url=fastgpt_base_url,
            api_key=fastgpt_api_key
        )
        agent = WorkflowAgent(fastgpt_client)
    
    result = await agent.chat(request.team_id, request.message)
    return ChatResponse(
        session_id=request.session_id or str(uuid.uuid4()),
        message=result.get("message", ""),
        workflow=result.get("workflow")
    )


@app.post("/api/ai-workflow/generate")
async def generate_workflow(request: GenerateRequest):
    """Generate a new workflow from user intent"""
    global agent
    if agent is None:
        from ..tools.fastgpt import FastGPTClient
        from ..agent.workflow_generator import WorkflowGenerator
        from ..agent.intent_analyzer import IntentAnalyzer
        
        fastgpt_base_url = os.environ.get("FASTGPT_API_URL", "http://fastgpt:3000")
        fastgpt_api_key = os.environ.get("FASTGPT_API_KEY", "")
        
        fastgpt_client = FastGPTClient(
            base_url=fastgpt_base_url,
            api_key=fastgpt_api_key
        )
        
        intent_analyzer = IntentAnalyzer()
        workflow_gen = WorkflowGenerator()
        agent = {
            "client": fastgpt_client,
            "intent_analyzer": intent_analyzer,
            "workflow_generator": workflow_gen
        }
    
    try:
        intent_result = await agent["intent_analyzer"].analyze(request.userIntent)
        
        workflow_result = await agent["workflow_generator"].generate(
            intent=intent_result.intent.value,
            complexity=intent_result.complexity.value,
            requirements=request.userIntent
        )
        
        session_id = request.sessionId or str(uuid.uuid4())
        
        return {
            "sessionId": session_id,
            "status": "ready" if workflow_result.is_valid else "failed",
            "message": "工作流已生成" if workflow_result.is_valid else "工作流生成失败",
            "workflow": {
                "nodes": [n.model_dump() for n in workflow_result.nodes],
                "edges": [e.model_dump() for e in workflow_result.edges]
            } if workflow_result.is_valid else None,
            "questions": None,
            "suggestions": None
        }
    except Exception as e:
        return {
            "sessionId": request.sessionId or str(uuid.uuid4()),
            "status": "error",
            "message": f"生成失败: {str(e)}",
            "workflow": None
        }


@app.post("/api/ai-workflow/optimize")
async def optimize_workflow(request: GenerateRequest):
    global agent
    if agent is None:
        from ..tools.fastgpt import FastGPTClient
        from ..agent.workflow_generator import WorkflowGenerator
        from ..agent.intent_analyzer import IntentAnalyzer
        
        fastgpt_base_url = os.environ.get("FASTGPT_API_URL", "http://fastgpt:3000")
        fastgpt_api_key = os.environ.get("FASTGPT_API_KEY", "")
        
        fastgpt_client = FastGPTClient(
            base_url=fastgpt_base_url,
            api_key=fastgpt_api_key
        )
        
        intent_analyzer = IntentAnalyzer()
        workflow_gen = WorkflowGenerator()
        agent = {
            "client": fastgpt_client,
            "intent_analyzer": intent_analyzer,
            "workflow_generator": workflow_gen
        }
    
    try:
        existing_workflow = request.context.get("existingWorkflow") if request.context else None
        
        if not existing_workflow:
            return {
                "sessionId": request.sessionId or str(uuid.uuid4()),
                "status": "error",
                "message": "需要提供现有工作流进行优化",
                "workflow": None
            }
        
        intent_result = await agent["intent_analyzer"].analyze(request.userIntent)
        
        workflow_result = await agent["workflow_generator"].generate(
            intent="modify_workflow",
            complexity=intent_result.complexity.value,
            requirements=request.userIntent
        )
        
        session_id = request.sessionId or str(uuid.uuid4())
        
        return {
            "sessionId": session_id,
            "status": "ready" if workflow_result.is_valid else "failed",
            "message": "工作流已优化" if workflow_result.is_valid else "工作流优化失败",
            "workflow": {
                "nodes": [n.model_dump() for n in workflow_result.nodes],
                "edges": [e.model_dump() for e in workflow_result.edges]
            } if workflow_result.is_valid else None,
            "questions": None,
            "suggestions": None
        }
    except Exception as e:
        return {
            "sessionId": request.sessionId or str(uuid.uuid4()),
            "status": "error",
            "message": f"优化失败: {str(e)}",
            "workflow": None
        }


@app.post("/api/ai-workflow/confirm")
async def confirm_workflow(request: ConfirmRequest):
    global agent
    if agent is None:
        from ..tools.fastgpt import FastGPTClient
        from ..agent.workflow_generator import WorkflowGenerator
        from ..agent.intent_analyzer import IntentAnalyzer
        
        fastgpt_base_url = os.environ.get("FASTGPT_API_URL", "http://fastgpt:3000")
        fastgpt_api_key = os.environ.get("FASTGPT_API_KEY", "")
        
        fastgpt_client = FastGPTClient(
            base_url=fastgpt_base_url,
            api_key=fastgpt_api_key
        )
        
        intent_analyzer = IntentAnalyzer()
        workflow_gen = WorkflowGenerator()
        agent = {
            "client": fastgpt_client,
            "intent_analyzer": intent_analyzer,
            "workflow_generator": workflow_gen
        }
    
    try:
        session_id = request.sessionId or str(uuid.uuid4())
        
        if request.confirmed:
            return {
                "sessionId": session_id,
                "status": "completed",
                "message": "工作流已确认保存",
                "workflow": None,
                "questions": None
            }
        
        user_answer = request.answer or ""
        
        if not user_answer:
            return {
                "sessionId": session_id,
                "status": "need_more_info",
                "message": "请提供答案继续生成工作流",
                "workflow": None,
                "questions": None
            }
        
        context = request.context or {}
        previous_workflow = context.get("previousWorkflow")
        
        prompt = f"用户回答: {user_answer}"
        if previous_workflow:
            prompt += f"\n基于之前的工作流继续优化"
        
        intent_result = await agent["intent_analyzer"].analyze(prompt)
        
        workflow_result = await agent["workflow_generator"].generate(
            intent="create_workflow",
            complexity=intent_result.complexity.value,
            requirements=prompt
        )
        
        return {
            "sessionId": session_id,
            "status": "ready" if workflow_result.is_valid else "need_more_info",
            "message": "基于您的回答，工作流已更新" if workflow_result.is_valid else "请提供更多信息",
            "workflow": {
                "nodes": [n.model_dump() for n in workflow_result.nodes],
                "edges": [e.model_dump() for e in workflow_result.edges]
            } if workflow_result.is_valid else None,
            "questions": None
        }
    except Exception as e:
        return {
            "sessionId": request.sessionId or str(uuid.uuid4()),
            "status": "error",
            "message": f"确认失败: {str(e)}",
            "workflow": None,
            "questions": None
        }


class ValidateRequest(BaseModel):
    workflow: Optional[Dict[str, Any]] = None
    plugins: Optional[List[Dict[str, Any]]] = None


@app.post("/api/ai-workflow/validate")
async def validate_workflow(request: ValidateRequest):
    global agent
    if agent is None:
        from ..agent.workflow_generator import WorkflowGenerator
        workflow_gen = WorkflowGenerator()
        agent = {"workflow_generator": workflow_gen}
    
    try:
        workflow = request.workflow or {}
        nodes = workflow.get("nodes", [])
        edges = workflow.get("edges", [])
        
        result = await agent["workflow_generator"].validate(nodes, edges)
        
        return {
            "valid": result.is_valid,
            "errors": result.errors,
            "suggestions": result.warnings
        }
    except Exception as e:
        return {
            "valid": False,
            "errors": [str(e)],
            "suggestions": []
        }
