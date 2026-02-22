import httpx
from typing import Optional, Any


class FastGPTClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0
        )
    
    async def get_available_nodes(self, team_id: str) -> dict:
        response = await self.client.post(
            f"{self.base_url}/api/core/app/tool/getSystemToolTemplates",
            json={"teamId": team_id}
        )
        return response.json()
    
    async def create_http_tool(self, team_id: str, name: str, tool_list: list) -> str:
        response = await self.client.post(
            f"{self.base_url}/api/core/app/httpTools/create",
            json={
                "name": name,
                "teamId": team_id,
                "createType": "manual"
            }
        )
        return response.json()
    
    async def create_workflow(self, team_id: str, name: str, nodes: list, edges: list) -> dict:
        response = await self.client.post(
            f"{self.base_url}/api/core/app/create",
            json={
                "name": name,
                "teamId": team_id,
                "type": "workflow",
                "nodes": nodes,
                "edges": edges
            }
        )
        return response.json()
