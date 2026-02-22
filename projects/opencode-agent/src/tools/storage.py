from minio import Minio
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional


class StorageService:
    def __init__(self, minio_endpoint: str, access_key: str, secret_key: str):
        self.minio = Minio(
            minio_endpoint,
            access_key=access_key,
            secret_key=secret_key
        )
    
    async def save_code(self, team_id: str, plugin_id: str, code: bytes) -> str:
        path = f"plugins/{team_id}/{plugin_id}/source/main.py"
        self.minio.put_object(
            "fastgpt-plugins",
            path,
            code
        )
        return path
    
    async def get_code(self, team_id: str, plugin_id: str) -> bytes:
        path = f"plugins/{team_id}/{plugin_id}/source/main.py"
        response = self.minio.get_object("fastgpt-plugins", path)
        return response.read()


class DatabaseService:
    def __init__(self, mongodb_uri: str):
        self.client = AsyncIOMotorClient(mongodb_uri)
        self.db = self.client.fastgpt
    
    async def save_session(self, session_data: dict):
        await self.db.aiWorkflowSession.insert_one(session_data)
    
    async def get_session(self, session_id: str):
        return await self.db.aiWorkflowSession.find_one({"sessionId": session_id})
