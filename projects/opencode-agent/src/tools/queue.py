import redis.asyncio as redis
import json
from typing import Optional, Callable


class TaskQueue:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    async def enqueue(self, task_type: str, payload: dict):
        await self.redis.lpush(
            f"queue:{task_type}",
            json.dumps(payload)
        )
    
    async def dequeue(self, task_type: str) -> Optional[dict]:
        result = await self.redis.brpop(
            f"queue:{task_type}",
            timeout=30
        )
        if result:
            return json.loads(result[1])
        return None
    
    async def process_queue(self, task_type: str, handler: Callable):
        while True:
            task = await self.dequeue(task_type)
            if task:
                await handler(task)
