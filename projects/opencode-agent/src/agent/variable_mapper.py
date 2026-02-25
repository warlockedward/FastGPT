"""
Variable Mapping Engine - Maps node outputs to inputs using Embedding + rules
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from pydantic import BaseModel
import httpx


class ConfidenceLevel(str, Enum):
    HIGH = "high"  # > 0.85 - auto connect
    MEDIUM = "medium"  # 0.6-0.85 - dashed line, user confirm
    LOW = "low"  # < 0.6 - no connection, prompt user


class VariableMapping(BaseModel):
    """Represents a variable mapping between nodes"""

    source_node_id: str
    source_variable: str
    target_node_id: str
    target_variable: str
    confidence: float
    confidence_level: ConfidenceLevel
    reason: str


class MappingResult(BaseModel):
    """Result of variable mapping operation"""

    mappings: List[VariableMapping]
    unmapped_inputs: List[Dict[str, str]]  # inputs that couldn't be mapped
    unmapped_outputs: List[Dict[str, str]]  # outputs that couldn't be mapped


class TypeCompatibilityMatrix:
    """Type compatibility matrix for FastGPT workflow nodes"""

    COMPATIBLE_TYPES = {
        "string": ["string", "text"],
        "number": ["number", "int", "float"],
        "boolean": ["boolean", "bool"],
        "array": ["array", "list"],
        "object": ["object", "json"],
        "any": ["string", "number", "boolean", "array", "object"],
    }

    @classmethod
    def is_compatible(cls, source_type: str, target_type: str) -> bool:
        source_type = source_type.lower()
        target_type = target_type.lower()

        if source_type == target_type:
            return True

        for compatible_targets in cls.COMPATIBLE_TYPES.values():
            if source_type in compatible_targets and target_type in compatible_targets:
                return True

        return False


class VariableMappingEngine:
    """Engine for mapping node outputs to inputs using Embedding + rules"""

    # Common variable name synonyms for semantic matching
    VARIABLE_SYNONYMS = {
        "user_input": ["userInput", "user_query", "query", "question", "input", "text"],
        "user_question": ["userInput", "user_query", "query", "question", "input"],
        "system_prompt": [
            "systemPrompt",
            "system_prompt",
            "system",
            "prompt",
            "instruction",
        ],
        "ai_response": ["response", "responseText", "answer", "output", "result"],
        "history": ["history", "chat_history", "conversation_history", "messages"],
        "knowledge_result": ["quoteList", "search_result", "dataset_result", "context"],
        "extracted_data": ["extractedFields", "extracted", "parsed", "data"],
    }

    def __init__(
        self, embedding_url: Optional[str] = None, embedding_model: str = "bge-m3"
    ):
        self.embedding_url = embedding_url or os.environ.get(
            "EMBEDDING_URL", os.environ.get("VLLM_BASE_URL", "http://localhost:8000")
        )
        self.embedding_model = embedding_model
        self.client = httpx.AsyncClient(timeout=30.0)
        self._cache = {}  # Variable similarity cache

    async def close(self):
        await self.client.aclose()

    def _get_synonyms(self, var_name: str) -> List[str]:
        """Get synonyms for a variable name"""
        var_lower = var_name.lower().replace("_", "")

        for key, synonyms in self.VARIABLE_SYNONYMS.items():
            if key.replace("_", "") == var_lower or var_lower in [
                s.replace("_", "") for s in synonyms
            ]:
                return [var_name] + synonyms

        return [var_name]

    def _calculate_similarity(self, var1: str, var2: str) -> float:
        """Calculate similarity between two variable names"""
        # Check cache first
        cache_key = f"{var1}:{var2}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Exact match
        if var1.lower() == var2.lower():
            self._cache[cache_key] = 1.0
            return 1.0

        # Check synonyms
        synonyms1 = self._get_synonyms(var1)
        synonyms2 = self._get_synonyms(var2)

        for s1 in synonyms1:
            for s2 in synonyms2:
                if s1.lower() == s2.lower():
                    self._cache[cache_key] = 0.95
                    return 0.95

        # Substring matching
        if var1.lower() in var2.lower() or var2.lower() in var1.lower():
            self._cache[cache_key] = 0.7
            return 0.7

        # Default low similarity
        self._cache[cache_key] = 0.3
        return 0.3

    def _calculate_confidence(
        self,
        source_var: str,
        target_var: str,
        source_type: str,
        target_type: str,
        source_node_type: str,
        target_node_type: str,
    ) -> Tuple[float, str]:
        """Calculate confidence score for a variable mapping"""

        # Semantic similarity
        similarity = self._calculate_similarity(source_var, target_var)

        # Type compatibility
        type_compatible = TypeCompatibilityMatrix.is_compatible(
            source_type, target_type
        )

        # Node function compatibility (rules-based)
        node_compatible = self._check_node_compatibility(
            source_node_type, target_node_type
        )

        # Calculate final confidence
        confidence = similarity * 0.5

        if type_compatible:
            confidence += 0.3
        else:
            return 0.1, f"Type mismatch: {source_type} -> {target_type}"

        if node_compatible:
            confidence += 0.2
        else:
            return (
                0.2,
                f"Node compatibility issue: {source_node_type} -> {target_node_type}",
            )

        # Cap at 1.0
        confidence = min(confidence, 1.0)

        reason = f"Similarity: {similarity:.2f}, Type compatible: {type_compatible}, Node compatible: {node_compatible}"

        return confidence, reason

    def _check_node_compatibility(
        self, source_node_type: str, target_node_type: str
    ) -> bool:
        """Check if two node types are compatible for connection"""

        # Define compatible connections
        compatible_connections = {
            "workflowStart": [
                "chatNode",
                "datasetSearchNode",
                "ifElseNode",
                "formInput",
                "userSelect",
            ],
            "chatNode": [
                "answerNode",
                "ifElseNode",
                "code",
                "httpRequest468",
                "datasetSearchNode",
                "classifyQuestion",
            ],
            "datasetSearchNode": ["chatNode", "datasetConcatNode", "contentExtract"],
            "datasetConcatNode": ["chatNode", "contentExtract"],
            "answerNode": [],  # Terminal node
            "ifElseNode": [
                "chatNode",
                "datasetSearchNode",
                "code",
                "httpRequest468",
                "answerNode",
            ],
            "code": ["chatNode", "answerNode", "httpRequest468"],
            "httpRequest468": ["chatNode", "answerNode", "code"],
            "classifyQuestion": ["chatNode", "answerNode", "datasetSearchNode"],
            "contentExtract": ["chatNode", "answerNode"],
            "agent": ["answerNode", "chatNode", "ifElseNode"],
        }

        compatible = compatible_connections.get(target_node_type, [])
        return source_node_type in compatible

    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Determine confidence level from score"""
        if confidence > 0.85:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.6:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    async def map_variables(
        self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]
    ) -> MappingResult:
        """
        Map variables from node outputs to node inputs.

        Args:
            nodes: List of workflow nodes with inputs/outputs
            edges: Existing edges between nodes

        Returns:
            MappingResult with automatic mappings and unmapped items
        """
        mappings = []
        unmapped_inputs = []
        unmapped_outputs = []

        # Build node lookup
        node_map = {node.get("nodeId"): node for node in nodes}

        # Get existing connections
        connected = set()
        for edge in edges:
            connected.add(edge.get("target"))

        # For each node (except workflowStart), find mappings
        for node in nodes:
            node_id = node.get("nodeId")
            node_type = node.get("flowNodeType")
            inputs = node.get("inputs", [])

            # Skip workflowStart
            if node_type == "workflowStart":
                continue

            # For each input, try to find a matching output
            for input_var in inputs:
                input_key = input_var.get("key", "")
                input_type = input_var.get("valueType", "string")

                # Find potential source nodes (connected or previous nodes)
                potential_sources = []

                # Find nodes that connect to this node
                for edge in edges:
                    if edge.get("target") == node_id:
                        source_id = edge.get("source")
                        if source_id in node_map:
                            potential_sources.append(node_map[source_id])

                # Also consider all previous nodes
                for prev_node in nodes:
                    if prev_node.get("nodeId") != node_id:
                        # Check if there's a path (simplified - just check all previous)
                        potential_sources.append(prev_node)

                # Find best match
                best_match = None
                best_confidence = 0
                best_reason = ""

                for source_node in potential_sources:
                    source_outputs = source_node.get("outputs", [])

                    for output_var in source_outputs:
                        output_key = output_var.get("key", "")
                        output_type = output_var.get("valueType", "string")

                        confidence, reason = self._calculate_confidence(
                            output_key,
                            input_key,
                            output_type,
                            input_type,
                            source_node.get("flowNodeType"),
                            node_type,
                        )

                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_match = {
                                "source_node_id": source_node.get("nodeId"),
                                "source_variable": output_key,
                                "target_node_id": node_id,
                                "target_variable": input_key,
                            }
                            best_reason = reason

                if best_match and best_confidence >= 0.6:
                    mappings.append(
                        VariableMapping(
                            source_node_id=best_match["source_node_id"],
                            source_variable=best_match["source_variable"],
                            target_node_id=best_match["target_node_id"],
                            target_variable=best_match["target_variable"],
                            confidence=best_confidence,
                            confidence_level=self._get_confidence_level(
                                best_confidence
                            ),
                            reason=best_reason,
                        )
                    )
                else:
                    unmapped_inputs.append(
                        {"node_id": node_id, "variable": input_key, "type": input_type}
                    )

        # Track unmapped outputs
        mapped_output_vars = set()
        for m in mappings:
            mapped_output_vars.add(f"{m.source_node_id}:{m.source_variable}")

        for node in nodes:
            node_id = node.get("nodeId")
            outputs = node.get("outputs", [])
            for output_var in outputs:
                output_key = output_var.get("key", "")
                if f"{node_id}:{output_key}" not in mapped_output_vars:
                    unmapped_outputs.append(
                        {
                            "node_id": node_id,
                            "variable": output_key,
                            "type": output_var.get("valueType", "string"),
                        }
                    )

        return MappingResult(
            mappings=mappings,
            unmapped_inputs=unmapped_inputs,
            unmapped_outputs=unmapped_outputs,
        )

    def get_automated_mappings(
        self, mapping_result: MappingResult
    ) -> List[VariableMapping]:
        """Get only high-confidence mappings that can be automated"""
        return [
            m
            for m in mapping_result.mappings
            if m.confidence_level == ConfidenceLevel.HIGH
        ]

    def get_user_confirm_mappings(
        self, mapping_result: MappingResult
    ) -> List[VariableMapping]:
        """Get medium-confidence mappings that need user confirmation"""
        return [
            m
            for m in mapping_result.mappings
            if m.confidence_level == ConfidenceLevel.MEDIUM
        ]
