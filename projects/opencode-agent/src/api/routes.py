from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List


app = FastAPI()


class ChatRequest(BaseModel):
    team_id: str
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    workflow: Optional[dict] = None


fastgpt_client = None
agent = None


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    global agent
    if agent is None:
        from ..tools.fastgpt import FastGPTClient
        from ..agent.core import WorkflowAgent
        
        fastgpt_client = FastGPTClient(
            base_url="http://fastgpt:3000",
            api_key="your-api-key"
        )
        agent = WorkflowAgent(fastgpt_client)
    
    result = await agent.chat(request.team_id, request.message)
    return ChatResponse(
        session_id=request.session_id or "new",
        message=result.get("message", ""),
        workflow=result.get("workflow")
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
