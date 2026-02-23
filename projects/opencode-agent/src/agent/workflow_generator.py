"""
WorkflowGenerator - Generates valid FastGPT workflow nodes from requirements
"""
import json
import os
import uuid
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import httpx


class FlowNodeType(str, Enum):
    """FastGPT workflow node types"""
    WORKFLOW_START = "workflowStart"
    CHAT_NODE = "chatNode"
    DATASET_SEARCH = "datasetSearchNode"
    DATASET_CONCAT = "datasetConcatNode"
    ANSWER_NODE = "answerNode"
    CLASSIFY_QUESTION = "classifyQuestion"
    CONTENT_EXTRACT = "contentExtract"
    HTTP_REQUEST = "httpRequest468"
    IF_ELSE = "ifElseNode"
    CODE = "code"
    LOOP = "loop"
    TOOL_CALL = "toolCall"
    AGENT = "agent"


class Position(BaseModel):
    """Node position in workflow canvas"""
    x: float = 0
    y: float = 0


class WorkflowNode(BaseModel):
    """A single node in the workflow"""
    nodeId: str
    flowNodeType: str
    name: str
    position: Position = Field(default_factory=Position)
    inputs: List[Dict[str, Any]] = Field(default_factory=list)
    outputs: List[Dict[str, Any]] = Field(default_factory=list)


class WorkflowEdge(BaseModel):
    """Connection between nodes"""
    source: str
    sourceHandle: str
    target: str
    targetHandle: str


class WorkflowResult(BaseModel):
    """Result of workflow generation"""
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    is_valid: bool = True
    errors: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Result of workflow validation"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class WorkflowGenerator:
    """Generates valid FastGPT workflows from requirements"""
    
    # Node templates for different complexity levels
    SIMPLE_NODES = [
        FlowNodeType.WORKFLOW_START,
        FlowNodeType.CHAT_NODE,
        FlowNodeType.ANSWER_NODE
    ]
    
    MEDIUM_NODES = [
        FlowNodeType.WORKFLOW_START,
        FlowNodeType.DATASET_SEARCH,
        FlowNodeType.CHAT_NODE,
        FlowNodeType.ANSWER_NODE
    ]
    
    COMPLEX_NODES = [
        FlowNodeType.WORKFLOW_START,
        FlowNodeType.DATASET_SEARCH,
        FlowNodeType.CHAT_NODE,
        FlowNodeType.IF_ELSE,
        FlowNodeType.CODE,
        FlowNodeType.ANSWER_NODE
    ]
    
    SYSTEM_PROMPT = """You are an AI Workflow generator. Generate a valid FastGPT workflow based on user requirements.

Available node types:
- workflowStart: Entry point for the workflow
- chatNode: AI chat node for processing user messages
- datasetSearchNode: Search a knowledge base
- answerNode: Output the final answer
- classifyQuestion: Classify user intent
- contentExtract: Extract structured data from content
- httpRequest468: Make HTTP requests
- ifElseNode: Conditional branching
- code: Execute custom code
- loop: Loop over items
- toolCall: Call external tools
- agent: AI agent with planning

Respond with a JSON object:
{
  "nodes": [
    {"nodeId": "unique_id", "flowNodeType": "node_type", "name": "Node Name"}
  ],
  "edges": [
    {"source": "source_id", "sourceHandle": "out", "target": "target_id", "targetHandle": "in"}
  ]
}

Ensure:
1. workflowStart is the entry point
2. answerNode is the final output
3. Edges connect nodes in logical flow
4. Each node has unique ID"""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or os.environ.get("FASTGPT_API_URL", "http://fastgpt:3000")
        self.api_key = api_key or os.environ.get("FASTGPT_API_KEY", "")
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def _generate_id(self) -> str:
        """Generate unique node ID"""
        return f"node_{uuid.uuid4().hex[:8]}"
    
    def _get_nodes_for_complexity(self, complexity: str, requirements: str) -> List[str]:
        """Determine which nodes to create based on complexity and requirements"""
        requirements_lower = requirements.lower()
        
        # Check for specific keywords
        has_knowledge_base = any(kw in requirements_lower for kw in [
            "knowledge", "knowledge base", "kb", "dataset", "search", "rag"
        ])
        has_conditionals = any(kw in requirements_lower for kw in [
            "if", "condition", "conditional", "branch", "check", "authentication", "auth"
        ])
        has_code = any(kw in requirements_lower for kw in [
            "code", "custom", "process", "transform", "calculate"
        ])
        has_notification = any(kw in requirements_lower for kw in [
            "notification", "notify", "send", "email", "webhook", "alert"
        ])
        
        if complexity == "simple":
            nodes = [FlowNodeType.WORKFLOW_START, FlowNodeType.CHAT_NODE, FlowNodeType.ANSWER_NODE]
        elif complexity == "complex":
            # Complex: always add more nodes regardless of keywords
            nodes = [FlowNodeType.WORKFLOW_START]
            if has_knowledge_base:
                nodes.append(FlowNodeType.DATASET_SEARCH)
            if has_conditionals:
                nodes.append(FlowNodeType.IF_ELSE)
            if has_code:
                nodes.append(FlowNodeType.CODE)
            if has_notification:
                nodes.append(FlowNodeType.HTTP_REQUEST)
            nodes.extend([FlowNodeType.CHAT_NODE, FlowNodeType.ANSWER_NODE])
        elif complexity == "medium" or has_knowledge_base:
            nodes = [FlowNodeType.WORKFLOW_START]
            if has_knowledge_base:
                nodes.append(FlowNodeType.DATASET_SEARCH)
            nodes.extend([FlowNodeType.CHAT_NODE, FlowNodeType.ANSWER_NODE])
        
        return nodes
    
    def _create_node(self, node_type: str, node_id: str, index: int, total: int) -> WorkflowNode:
        """Create a single node with proper configuration"""
        name_map = {
            FlowNodeType.WORKFLOW_START.value: "Workflow Start",
            FlowNodeType.CHAT_NODE.value: "AI Chat",
            FlowNodeType.DATASET_SEARCH.value: "Knowledge Base Search",
            FlowNodeType.DATASET_CONCAT.value: "Knowledge Base Concat",
            FlowNodeType.ANSWER_NODE.value: "Answer",
            FlowNodeType.CLASSIFY_QUESTION.value: "Intent Classification",
            FlowNodeType.CONTENT_EXTRACT.value: "Content Extract",
            FlowNodeType.HTTP_REQUEST.value: "HTTP Request",
            FlowNodeType.IF_ELSE.value: "Conditional",
            FlowNodeType.CODE.value: "Code",
            FlowNodeType.LOOP.value: "Loop",
            FlowNodeType.TOOL_CALL.value: "Tool Call",
            FlowNodeType.AGENT.value: "AI Agent"
        }
        
        # Calculate position - vertical flow with slight horizontal offset
        x = 250  # Center
        y = index * 200  # Vertical spacing
        
        return WorkflowNode(
            nodeId=node_id,
            flowNodeType=node_type,
            name=name_map.get(node_type, node_type),
            position=Position(x=x, y=y),
            inputs=[],
            outputs=[]
        )
    
    def _create_edges(self, nodes: List[WorkflowNode]) -> List[WorkflowEdge]:
        """Create edges connecting nodes in sequence"""
        edges = []
        
        for i in range(len(nodes) - 1):
            edges.append(WorkflowEdge(
                source=nodes[i].nodeId,
                sourceHandle="out",
                target=nodes[i + 1].nodeId,
                targetHandle="in"
            ))
        
        return edges
    
    async def generate(
        self,
        intent: str,
        complexity: str,
        requirements: str
    ) -> WorkflowResult:
        """
        Generate a workflow based on intent, complexity, and requirements.
        
        Args:
            intent: User intent (create_workflow, modify_workflow, etc.)
            complexity: simple, medium, or complex
            requirements: Natural language requirements
            
        Returns:
            WorkflowResult with nodes and edges
        """
        try:
            # Determine which nodes to create
            node_types = self._get_nodes_for_complexity(complexity, requirements)
            
            # Create nodes
            nodes = []
            for i, node_type in enumerate(node_types):
                node_id = self._generate_id()
                node = self._create_node(node_type.value, node_id, i, len(node_types))
                nodes.append(node)
            
            # Create edges
            edges = self._create_edges(nodes)
            
            return WorkflowResult(nodes=nodes, edges=edges)
            
        except Exception as e:
            return WorkflowResult(
                nodes=[],
                edges=[],
                is_valid=False,
                errors=[f"Failed to generate workflow: {str(e)}"]
            )
    
    async def validate(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Validate a workflow structure.
        
        Args:
            nodes: List of node dictionaries
            edges: List of edge dictionaries
            
        Returns:
            ValidationResult with validation status and errors
        """
        errors = []
        warnings = []
        
        # Check for nodes
        if not nodes:
            errors.append("Workflow must have at least one node")
            return ValidationResult(is_valid=False, errors=errors)
        
        # Check for workflowStart
        node_types = [n.get("flowNodeType") for n in nodes]
        if FlowNodeType.WORKFLOW_START.value not in node_types:
            errors.append("Workflow must have a workflowStart node")
        
        # Check for answerNode
        if FlowNodeType.ANSWER_NODE.value not in node_types:
            warnings.append("Workflow should have an answerNode as final output")
        
        # Check for orphan nodes (no connections)
        node_ids = set(n.get("nodeId") for n in nodes)
        
        connected_nodes = set()
        for edge in edges:
            connected_nodes.add(edge.get("source"))
            connected_nodes.add(edge.get("target"))
        
        orphan_nodes = node_ids - connected_nodes
        if orphan_nodes and len(nodes) > 1:
            warnings.append(f"Orphan nodes detected (not connected): {orphan_nodes}")
        
        # Check for edges with invalid node references
        for edge in edges:
            if edge.get("source") not in node_ids:
                errors.append(f"Edge references non-existent source node: {edge.get('source')}")
            if edge.get("target") not in node_ids:
                errors.append(f"Edge references non-existent target node: {edge.get('target')}")
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
