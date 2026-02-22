from typing import List, Dict, Any


class WorkflowAgent:
    def __init__(self, fastgpt_client):
        self.client = fastgpt_client
        self.conversation_history = []
    
    async def analyze_intent(self, message: str) -> Dict[str, Any]:
        return {
            "intent": "create_workflow",
            "complexity": "simple",
            "needs_plugin": False
        }
    
    async def get_available_nodes(self, team_id: str) -> List[Dict]:
        result = await self.client.get_available_nodes(team_id)
        return result.get("data", [])
    
    async def generate_workflow(self, team_id: str, requirements: str) -> Dict:
        nodes = await self.get_available_nodes(team_id)
        
        workflow = {
            "nodes": [
                {"flowNodeType": "workflowStart", "id": "start"},
                {"flowNodeType": "chatNode", "id": "chat"}
            ],
            "edges": [
                {"source": "start", "target": "chat"}
            ]
        }
        
        return workflow
    
    async def chat(self, team_id: str, message: str) -> Dict[str, Any]:
        intent = await self.analyze_intent(message)
        
        if intent["intent"] == "create_workflow":
            workflow = await self.generate_workflow(team_id, message)
            return {
                "message": "已生成工作流",
                "workflow": workflow
            }
        
        return {"message": "理解了你的需求"}
