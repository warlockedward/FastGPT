"""
RAG Knowledge Base - Workflow case storage and retrieval using Milvus
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
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class WorkflowCase(BaseModel):
    id: str
    intent: str
    topology: List[str]
    nodes_count: int
    edges_count: int
    key_prompts: str
    version: str
    tags: List[str]
    status: CaseStatus
    created_at: str
    updated_at: str
    embedding: Optional[List[float]] = None


class RetrievalResult(BaseModel):
    cases: List[WorkflowCase]
    total: int
    query_embedding: Optional[List[float]] = None


class RAGKnowledgeBase:
    def __init__(
        self,
        milvus_url: Optional[str] = None,
        milvus_token: Optional[str] = None,
        db_url: Optional[str] = None,
    ):
        self.milvus_url = milvus_url or os.environ.get(
            "MILVUS_URL", "http://localhost:19530"
        )
        self.milvus_token = milvus_token or os.environ.get("MILVUS_TOKEN", "")
        self.collection_name = "workflow_cases"
        self.db_url = db_url or os.environ.get(
            "MONGODB_URI", "mongodb://localhost:27017"
        )
        self.client = httpx.AsyncClient(timeout=30.0)
        self._local_cache = []

    async def close(self):
        await self.client.aclose()

    def _generate_id(self, intent: str) -> str:
        return hashlib.md5(
            f"{intent}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

    def _extract_topology(self, nodes: List[Dict], edges: List[Dict]) -> List[str]:
        topology = []
        sorted_nodes = sorted(nodes, key=lambda n: n.get("position", {}).get("x", 0))
        for node in sorted_nodes:
            node_type = node.get("flowNodeType", "unknown")
            topology.append(node_type)
        return topology

    def _generate_embedding(self, text: str) -> List[float]:
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        dim = 768
        embedding = []
        for i in range(dim):
            embedding.append(((hash_val >> i) % 1000) / 1000.0)
        return embedding

    async def _ensure_collection(self):
        try:
            response = await self.client.post(
                f"{self.milvus_url}/api/v1/collection",
                json={
                    "collection_name": self.collection_name,
                    "dimension": 768,
                    "metric_type": "IP",
                    "description": "Workflow cases for RAG",
                },
                headers={"Authorization": f"Bearer {self.milvus_token}"}
                if self.milvus_token
                else {},
            )
        except Exception:
            pass

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

        self._local_cache.append(case.model_dump())

        try:
            await self._store_in_milvus(case)
        except Exception:
            pass

        return case

    async def _store_in_milvus(self, case: WorkflowCase):
        if case.embedding is None:
            return

        try:
            await self.client.insert(
                collection_name=self.collection_name,
                records=[
                    {
                        "id": case.id,
                        "vector": case.embedding,
                        "intent": case.intent,
                        "topology": json.dumps(case.topology),
                        "status": case.status.value,
                        "version": case.version,
                        "tags": json.dumps(case.tags),
                    }
                ],
                headers={"Authorization": f"Bearer {self.milvus_token}"}
                if self.milvus_token
                else {},
            )
        except Exception as e:
            if "collection" in str(e).lower():
                await self._ensure_collection()
                await self.client.insert(
                    collection_name=self.collection_name,
                    records=[
                        {
                            "id": case.id,
                            "vector": case.embedding,
                            "intent": case.intent,
                            "topology": json.dumps(case.topology),
                            "status": case.status.value,
                            "version": case.version,
                            "tags": json.dumps(case.tags),
                        }
                    ],
                    headers={"Authorization": f"Bearer {self.milvus_token}"}
                    if self.milvus_token
                    else {},
                )

    async def retrieve_similar(
        self,
        query: str,
        limit: int = 5,
        status_filter: Optional[CaseStatus] = None,
        version: Optional[str] = None,
    ) -> RetrievalResult:
        query_embedding = self._generate_embedding(query)

        try:
            cases = await self._retrieve_from_milvus(
                query_embedding, limit, status_filter, version
            )
            if cases:
                return RetrievalResult(
                    cases=cases, total=len(cases), query_embedding=query_embedding
                )
        except Exception:
            pass

        cases = self._retrieve_from_cache(query, limit, status_filter, version)

        return RetrievalResult(
            cases=cases, total=len(cases), query_embedding=query_embedding
        )

    async def _retrieve_from_milvus(
        self,
        query_embedding: List[float],
        limit: int,
        status_filter: Optional[CaseStatus],
        version: Optional[str],
    ) -> List[WorkflowCase]:
        filter_expr = "1==1"
        if status_filter:
            filter_expr = f'status == "{status_filter.value}"'
        if version:
            filter_expr += f' and version == "{version}"'

        try:
            response = await self.client.search(
                collection_name=self.collection_name,
                vector=query_embedding,
                limit=limit,
                filter=filter_expr,
                output_fields=["id", "intent", "topology", "status", "version", "tags"],
                headers={"Authorization": f"Bearer {self.milvus_token}"}
                if self.milvus_token
                else {},
            )

            results = response.get("results", [])

            cases = []
            for r in results:
                fields = r.get("entity", {})
                cases.append(
                    WorkflowCase(
                        id=fields.get("id", ""),
                        intent=fields.get("intent", ""),
                        topology=json.loads(fields.get("topology", "[]")),
                        nodes_count=0,
                        edges_count=0,
                        key_prompts="",
                        version=fields.get("version", ""),
                        tags=json.loads(fields.get("tags", "[]")),
                        status=CaseStatus(fields.get("status", "success")),
                        created_at="",
                        updated_at="",
                    )
                )

            return cases
        except Exception as e:
            raise Exception(f"Milvus search failed: {str(e)}")

    def _retrieve_from_cache(
        self,
        query: str,
        limit: int,
        status_filter: Optional[CaseStatus],
        version: Optional[str],
    ) -> List[WorkflowCase]:
        query_lower = query.lower()
        results = []

        for case_dict in self._local_cache:
            if status_filter and case_dict.get("status") != status_filter.value:
                continue
            if version and case_dict.get("version") != version:
                continue

            if query_lower in case_dict.get("intent", "").lower():
                results.append(WorkflowCase(**case_dict))

            for tag in case_dict.get("tags", []):
                if query_lower in tag.lower():
                    results.append(WorkflowCase(**case_dict))
                    break

        return results[:limit]

    async def retrieve_positive_cases(
        self, query: str, limit: int = 3
    ) -> RetrievalResult:
        return await self.retrieve_similar(
            query, limit, status_filter=CaseStatus.SUCCESS
        )

    async def retrieve_negative_cases(
        self, query: str, limit: int = 3
    ) -> RetrievalResult:
        return await self.retrieve_similar(
            query, limit, status_filter=CaseStatus.FAILED
        )

    async def get_system_prompt_context(
        self, query: str, include_positive: bool = True, include_negative: bool = True
    ) -> str:
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
        for case_dict in self._local_cache:
            if case_dict.get("id") == case_id:
                if was_modified:
                    case_dict["status"] = CaseStatus.PARTIAL.value
                if error_log:
                    case_dict["key_prompts"] += f"\n[ERROR]: {error_log}"

                case_dict["updated_at"] = datetime.now().isoformat()
                return True

        return False
