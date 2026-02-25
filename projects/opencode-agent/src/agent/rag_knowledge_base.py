"""
RAG Knowledge Base - Workflow case storage and retrieval
"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel
import httpx


class CaseStatus(str, Enum):
    """Workflow case status"""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class WorkflowCase(BaseModel):
    """A workflow case for RAG"""

    id: str
    intent: str
    topology: List[str]  # Node type sequence
    nodes_count: int
    edges_count: int
    key_prompts: str
    version: str
    tags: List[str]
    status: CaseStatus
    created_at: str
    updated_at: str

    # For embedding
    embedding: Optional[List[float]] = None


class RetrievalResult(BaseModel):
    """Result of case retrieval"""

    cases: List[WorkflowCase]
    total: int
    query_embedding: Optional[List[float]] = None


class RAGKnowledgeBase:
    """RAG Knowledge Base for workflow cases"""

    def __init__(
        self, vector_store_url: Optional[str] = None, db_url: Optional[str] = None
    ):
        self.vector_store_url = vector_store_url or os.environ.get(
            "VECTOR_STORE_URL", "http://localhost:6333"
        )
        self.db_url = db_url or os.environ.get(
            "MONGODB_URI", "mongodb://localhost:27017"
        )
        self.client = httpx.AsyncClient(timeout=30.0)
        self._local_cache = []  # In-memory cache for development

    async def close(self):
        await self.client.aclose()

    def _generate_id(self, intent: str) -> str:
        """Generate unique ID for a case"""
        return hashlib.md5(
            f"{intent}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

    def _extract_topology(self, nodes: List[Dict], edges: List[Dict]) -> List[str]:
        """Extract node topology from workflow"""
        topology = []

        # Get node types in order (by position x)
        sorted_nodes = sorted(nodes, key=lambda n: n.get("position", {}).get("x", 0))
        for node in sorted_nodes:
            node_type = node.get("flowNodeType", "unknown")
            topology.append(node_type)

        return topology

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (simplified - in production use actual embedding model)"""
        # Simple hash-based embedding for development
        # In production, replace with actual embedding API call
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)

        # Generate a fixed-size vector
        dim = 384  # Common embedding dimension
        embedding = []
        for i in range(dim):
            embedding.append(((hash_val >> i) % 1000) / 1000.0)

        return embedding

    async def store_case(
        self,
        intent: str,
        nodes: List[Dict],
        edges: List[Dict],
        key_prompts: str,
        version: str,
        tags: List[str],
        status: CaseStatus,
    ) -> WorkflowCase:
        """Store a workflow case"""

        topology = self._extract_topology(nodes, edges)

        case = WorkflowCase(
            id=self._generate_id(intent),
            intent=intent,
            topology=topology,
            nodes_count=len(nodes),
            edges_count=len(edges),
            key_prompts=key_prompts,
            version=version,
            tags=tags,
            status=status,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            embedding=self._generate_embedding(intent),
        )

        # Store locally for now (in production, store to vector DB)
        self._local_cache.append(case.model_dump())

        # Try to store in vector DB
        try:
            await self._store_in_vector_db(case)
        except Exception:
            pass  # Continue with local cache if vector DB unavailable

        return case

    async def _store_in_vector_db(self, case: WorkflowCase):
        """Store case in vector database (Qdrant)"""
        if case.embedding is None:
            return

        await self.client.post(
            f"{self.vector_store_url}/collections/workflow_cases/points",
            json={
                "points": [
                    {
                        "id": int(case.id, 16),
                        "vector": case.embedding,
                        "payload": {
                            "intent": case.intent,
                            "topology": json.dumps(case.topology),
                            "status": case.status.value,
                            "version": case.version,
                        },
                    }
                ]
            },
        )

    async def retrieve_similar(
        self,
        query: str,
        limit: int = 5,
        status_filter: Optional[CaseStatus] = None,
        version: Optional[str] = None,
    ) -> RetrievalResult:
        """Retrieve similar workflow cases"""

        query_embedding = self._generate_embedding(query)

        # Try vector DB search first
        try:
            cases = await self._retrieve_from_vector_db(
                query_embedding, limit, status_filter, version
            )
            if cases:
                return RetrievalResult(
                    cases=cases, total=len(cases), query_embedding=query_embedding
                )
        except Exception:
            pass

        # Fallback to local cache with simple matching
        cases = self._retrieve_from_cache(query, limit, status_filter, version)

        return RetrievalResult(
            cases=cases, total=len(cases), query_embedding=query_embedding
        )

    async def _retrieve_from_vector_db(
        self,
        query_embedding: List[float],
        limit: int,
        status_filter: Optional[CaseStatus],
        version: Optional[str],
    ) -> List[WorkflowCase]:
        """Retrieve from vector database"""

        # Build filter
        filter_conditions = {}
        if status_filter:
            filter_conditions["status"] = status_filter.value
        if version:
            filter_conditions["version"] = version

        response = await self.client.post(
            f"{self.vector_store_url}/collections/workflow_cases/points/search",
            json={
                "vector": query_embedding,
                "limit": limit,
                "filter": filter_conditions if filter_conditions else None,
            },
        )

        if response.status_code != 200:
            return []

        results = response.json().get("result", [])

        cases = []
        for r in results:
            payload = r.get("payload", {})
            cases.append(
                WorkflowCase(
                    id=str(r.get("id")),
                    intent=payload.get("intent", ""),
                    topology=json.loads(payload.get("topology", "[]")),
                    nodes_count=0,
                    edges_count=0,
                    key_prompts="",
                    version=payload.get("version", ""),
                    tags=[],
                    status=CaseStatus(payload.get("status", "success")),
                    created_at="",
                    updated_at="",
                )
            )

        return cases

    def _retrieve_from_cache(
        self,
        query: str,
        limit: int,
        status_filter: Optional[CaseStatus],
        version: Optional[str],
    ) -> List[WorkflowCase]:
        """Retrieve from local cache using simple text matching"""

        query_lower = query.lower()
        results = []

        for case_dict in self._local_cache:
            # Apply filters
            if status_filter and case_dict.get("status") != status_filter.value:
                continue
            if version and case_dict.get("version") != version:
                continue

            # Simple text matching
            if query_lower in case_dict.get("intent", "").lower():
                results.append(WorkflowCase(**case_dict))

            # Also check tags
            for tag in case_dict.get("tags", []):
                if query_lower in tag.lower():
                    results.append(WorkflowCase(**case_dict))
                    break

        # Sort by relevance (simple - just return first N)
        return results[:limit]

    async def retrieve_positive_cases(
        self, query: str, limit: int = 3
    ) -> RetrievalResult:
        """Retrieve successful cases for reference"""
        return await self.retrieve_similar(
            query, limit, status_filter=CaseStatus.SUCCESS
        )

    async def retrieve_negative_cases(
        self, query: str, limit: int = 3
    ) -> RetrievalResult:
        """Retrieve failed cases as warnings"""
        return await self.retrieve_similar(
            query, limit, status_filter=CaseStatus.FAILED
        )

    async def get_system_prompt_context(
        self, query: str, include_positive: bool = True, include_negative: bool = True
    ) -> str:
        """Generate system prompt context from retrieved cases"""

        context_parts = []

        if include_positive:
            positive = await self.retrieve_positive_cases(query)
            if positive.cases:
                context_parts.append("## 参考成功案例:")
                for case in positive.cases:
                    context_parts.append(
                        f"- 意图: {case.intent}\n"
                        f"  拓扑: {' -> '.join(case.topology)}\n"
                        f"  关键提示: {case.key_prompts[:100]}..."
                    )

        if include_negative:
            negative = await self.retrieve_negative_cases(query)
            if negative.cases:
                context_parts.append("\n## 需要避免的问题:")
                for case in negative.cases:
                    context_parts.append(
                        f"- 意图: {case.intent}\n  问题: {case.key_prompts[:100]}..."
                    )

        if context_parts:
            return "\n\n".join(context_parts)

        return ""

    async def record_feedback(
        self, case_id: str, was_modified: bool, error_log: Optional[str] = None
    ) -> bool:
        """Record user feedback for a generated workflow"""

        # Find case in cache
        for case_dict in self._local_cache:
            if case_dict.get("id") == case_id:
                # Update status based on feedback
                if was_modified:
                    case_dict["status"] = CaseStatus.PARTIAL.value
                if error_log:
                    case_dict["key_prompts"] += f"\n[ERROR]: {error_log}"

                case_dict["updated_at"] = datetime.now().isoformat()

                # Try to update in vector DB
                try:
                    await self._update_in_vector_db(case_dict)
                except Exception:
                    pass

                return True

        return False

    async def _update_in_vector_db(self, case_dict: Dict):
        """Update case in vector database"""
        # Implementation would update the vector DB entry
        pass
