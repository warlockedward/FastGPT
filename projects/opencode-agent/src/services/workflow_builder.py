"""
WorkflowBuilder - Builds FastGPT workflows with complete node schemas

This module provides:
1. Full FastGPT workflow node/edge schema support
2. Automatic node positioning and layout
3. Node configuration with proper inputs/outputs
4. Workflow validation
5. Export to FastGPT-compatible JSON
"""
from __future__ import annotations
import uuid
import math
from enum import Enum
from typing import Optional, Dict, List, Any, Literal
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

from .component_registry import FlowNodeTypeEnum, ComponentRegistry


# ============================================================
# FastGPT Node Data Models (mirrors FastGPT's internal schema)
# ============================================================

class WorkflowIOValueType(str, Enum):
    """Workflow IO value types"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY_STRING = "arrayString"
    ARRAY_NUMBER = "arrayNumber"
    ARRAY_BOOLEAN = "arrayBoolean"
    ARRAY_OBJECT = "arrayObject"
    CHAT_HISTORY = "chatHistory"
    DATASET_QUOTE = "datasetQuote"
    ANY = "any"
    REFERENCE = "reference"  # Reference to other node output


class FlowNodeInputType(str, Enum):
    """Node input types"""
    REFERENCE = "reference"
    INPUT = "input"
    TEXTAREA = "textarea"
    NUMBER_INPUT = "numberInput"
    SWITCH = "switch"
    SELECT = "select"
    MULTIPLE_SELECT = "multipleSelect"
    JSON_EDITOR = "JSONEditor"
    ADD_INPUT_PARAM = "addInputParam"
    CUSTOM_VARIABLE = "customVariable"
    SELECT_APP = "selectApp"
    SELECT_LLM_MODEL = "selectLLMModel"
    SELECT_DATASET = "selectDataset"
    HIDDEN = "hidden"


@dataclass
class FlowNodeInput:
    """Input configuration for a node"""
    key: str
    label: str
    type: FlowNodeInputType
    required: bool = False
    description: str = ""
    default_value: Any = None
    value_type: WorkflowIOValueType = WorkflowIOValueType.STRING
    options: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class FlowNodeOutput:
    """Output configuration for a node"""
    key: str
    label: str
    type: str = "source"  # source, static, dynamic
    value_type: WorkflowIOValueType = WorkflowIOValueType.STRING
    description: str = ""


@dataclass
class Position:
    """Node position in canvas"""
    x: float
    y: float


@dataclass
class WorkflowNode:
    """
    A single node in FastGPT workflow.
    
    Mirrors FastGPT's FlowNodeItemType structure.
    """
    node_id: str
    flow_node_type: str
    position: Position
    data: Dict[str, Any] = field(default_factory=dict)
    inputs: List[FlowNodeInput] = field(default_factory=list)
    outputs: List[FlowNodeOutput] = field(default_factory=list)
    name: str = ""
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to FastGPT workflow JSON format"""
        return {
            "nodeId": self.node_id,
            "flowNodeType": self.flow_node_type,
            "position": {"x": self.position.x, "y": self.position.y},
            "data": self.data,
            "inputs": [
                {
                    "key": inp.key,
                    "label": inp.label,
                    "type": inp.type.value,
                    "required": inp.required,
                    "description": inp.description,
                    "defaultValue": inp.default_value,
                    "valueType": inp.value_type.value,
                    "options": inp.options
                }
                for inp in self.inputs
            ],
            "outputs": [
                {
                    "key": out.key,
                    "label": out.label,
                    "type": out.type,
                    "valueType": out.value_type.value,
                    "description": out.description
                }
                for out in self.outputs
            ]
        }


@dataclass
class WorkflowEdge:
    """Connection between nodes"""
    edge_id: str
    source: str
    target: str
    source_handle: str = "source"
    target_handle: str = "target"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "edgeId": self.edge_id,
            "source": self.source,
            "target": self.target,
            "sourceHandle": self.source_handle,
            "targetHandle": self.target_handle
        }


@dataclass
class WorkflowValidationError:
    """Validation error"""
    code: str
    message: str
    node_id: Optional[str] = None


@dataclass
class WorkflowValidationResult:
    """Result of workflow validation"""
    is_valid: bool
    errors: List[WorkflowValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class GeneratedWorkflow:
    """Generated workflow result"""
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
    validation: WorkflowValidationResult
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_fastgpt_format(self) -> Dict[str, Any]:
        """Export to FastGPT-compatible format"""
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges]
        }


# ============================================================
# Node Configuration Templates
# ============================================================

class NodeConfigTemplate:
    """Templates for node configurations"""
    
    @staticmethod
    def workflow_start() -> Dict[str, Any]:
        return {
            "isEntry": True,
            "isTool": False,
            "description": "工作流入口"
        }
    
    @staticmethod
    def chat_node(model: str = "gpt-4", prompt: str = "") -> Dict[str, Any]:
        return {
            "model": model,
            "systemPrompt": prompt,
            "description": "AI对话节点"
        }
    
    @staticmethod
    def answer_node() -> Dict[str, Any]:
        return {
            "description": "回答节点"
        }
    
    @staticmethod
    def dataset_search(
        dataset_id: Optional[str] = None,
        search_mode: str = "embedding",
        limit: int = 5
    ) -> Dict[str, Any]:
        return {
            "datasetId": dataset_id or "",
            "searchMode": search_mode,
            "limit": limit,
            "description": "知识库搜索"
        }
    
    @staticmethod
    def http_request(
        method: str = "GET",
        url: str = "",
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        return {
            "method": method,
            "url": url,
            "headers": headers or {},
            "body": "",
            "description": "HTTP请求"
        }
    
    @staticmethod
    def if_else(condition: str = "") -> Dict[str, Any]:
        return {
            "condition": condition,
            "description": "条件分支"
        }
    
    @staticmethod
    def code(
        code_type: str = "javascript",
        code: str = ""
    ) -> Dict[str, Any]:
        return {
            "codeType": code_type,
            "code": code,
            "description": "代码执行"
        }
    
    @staticmethod
    def classify_question(
        classes: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        return {
            "classes": classes or [
                {"name": "类别1", "description": "描述1"},
                {"name": "类别2", "description": "描述2"}
            ],
            "description": "问题分类"
        }
    
    @staticmethod
    def user_select(
        options: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        return {
            "options": options or ["选项1", "选项2"],
            "description": "用户选择"
        }
    
    @staticmethod
    def form_input(
        fields: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        return {
            "fields": fields or [
                {"key": "field1", "label": "字段1", "type": "string"}
            ],
            "description": "表单输入"
        }
    
    @staticmethod
    def plugin_module(plugin_id: Optional[str] = None) -> Dict[str, Any]:
        return {
            "pluginId": plugin_id or "",
            "description": "插件模块"
        }
    
    @staticmethod
    def agent(
        model: str = "gpt-4",
        system_prompt: str = ""
    ) -> Dict[str, Any]:
        return {
            "model": model,
            "systemPrompt": system_prompt,
            "description": "AI智能体"
        }


# ============================================================
# Workflow Builder
# ============================================================

class LayoutAlgorithm(str, Enum):
    """Layout algorithm for node positioning"""
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    AUTO = "auto"


class WorkflowBuilder:
    """
    Builder for FastGPT workflows with complete schema support.
    
    Features:
    - Full FastGPT node schema (inputs, outputs, data)
    - Automatic layout algorithms
    - Node configuration templates
    - Workflow validation
    - Export to FastGPT format
    """
    
    DEFAULT_NODE_SPACING_X = 300
    DEFAULT_NODE_SPACING_Y = 200
    
    def __init__(
        self,
        registry: Optional[ComponentRegistry] = None,
        layout: LayoutAlgorithm = LayoutAlgorithm.VERTICAL
    ):
        self.registry = registry or ComponentRegistry()
        self.layout = layout
        
        # Internal state
        self._nodes: List[WorkflowNode] = []
        self._edges: List[WorkflowEdge] = []
        self._node_counter = 0
        
        # Entry and exit nodes
        self._entry_node: Optional[str] = None
        self._exit_nodes: List[str] = []
    
    def _generate_id(self, prefix: str = "node") -> str:
        """Generate unique ID"""
        self._node_counter += 1
        return f"{prefix}_{uuid.uuid4().hex[:8]}"
    
    def _get_node_name(self, node_type: FlowNodeTypeEnum) -> str:
        """Get default name for node type"""
        names = {
            FlowNodeTypeEnum.WORKFLOW_START: "开始",
            FlowNodeTypeEnum.CHAT_NODE: "AI对话",
            FlowNodeTypeEnum.ANSWER_NODE: "回答",
            FlowNodeTypeEnum.DATASET_SEARCH_NODE: "知识库搜索",
            FlowNodeTypeEnum.DATASET_CONCAT_NODE: "知识库拼接",
            FlowNodeTypeEnum.CLASSIFY_QUESTION: "意图分类",
            FlowNodeTypeEnum.CONTENT_EXTRACT: "内容提取",
            FlowNodeTypeEnum.AGENT: "AI智能体",
            FlowNodeTypeEnum.IF_ELSE_NODE: "条件分支",
            FlowNodeTypeEnum.HTTP_REQUEST: "HTTP请求",
            FlowNodeTypeEnum.CODE: "代码执行",
            FlowNodeTypeEnum.USER_SELECT: "用户选择",
            FlowNodeTypeEnum.FORM_INPUT: "表单输入",
            FlowNodeTypeEnum.PLUGIN_MODULE: "插件",
        }
        return names.get(node_type, node_type.value)
    
    def _get_node_config(self, node_type: FlowNodeTypeEnum) -> Dict[str, Any]:
        """Get default config for node type"""
        templates = {
            FlowNodeTypeEnum.WORKFLOW_START: NodeConfigTemplate.workflow_start,
            FlowNodeTypeEnum.CHAT_NODE: NodeConfigTemplate.chat_node,
            FlowNodeTypeEnum.ANSWER_NODE: NodeConfigTemplate.answer_node,
            FlowNodeTypeEnum.DATASET_SEARCH_NODE: NodeConfigTemplate.dataset_search,
            FlowNodeTypeEnum.IF_ELSE_NODE: NodeConfigTemplate.if_else,
            FlowNodeTypeEnum.HTTP_REQUEST: NodeConfigTemplate.http_request,
            FlowNodeTypeEnum.CODE: NodeConfigTemplate.code,
            FlowNodeTypeEnum.CLASSIFY_QUESTION: NodeConfigTemplate.classify_question,
            FlowNodeTypeEnum.USER_SELECT: NodeConfigTemplate.user_select,
            FlowNodeTypeEnum.FORM_INPUT: NodeConfigTemplate.form_input,
            FlowNodeTypeEnum.PLUGIN_MODULE: NodeConfigTemplate.plugin_module,
            FlowNodeTypeEnum.AGENT: NodeConfigTemplate.agent,
        }
        
        template_fn = templates.get(node_type)
        if template_fn:
            return template_fn()
        return {"description": node_type.value}
    
    def add_node(
        self,
        node_type: FlowNodeTypeEnum,
        name: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        position: Optional[Position] = None,
        **kwargs
    ) -> str:
        """
        Add a node to the workflow.
        
        Args:
            node_type: Type of node to add
            name: Custom name (optional)
            config: Node configuration (optional)
            position: Node position (optional, auto-calculated if not provided)
            **kwargs: Additional configuration
            
        Returns:
            Node ID
        """
        node_id = self._generate_id(node_type.value)
        
        # Get or generate name
        node_name = name or self._get_node_name(node_type)
        
        # Get configuration
        node_config = config or self._get_node_config(node_type)
        node_config.update(kwargs)
        
        # Mark entry node
        if node_type == FlowNodeTypeEnum.WORKFLOW_START:
            self._entry_node = node_id
            node_config["isEntry"] = True
        
        # Mark exit nodes
        if node_type == FlowNodeTypeEnum.ANSWER_NODE:
            self._exit_nodes.append(node_id)
        
        # Calculate position if not provided
        if position is None:
            position = self._calculate_position(node_type)
        
        # Create node
        node = WorkflowNode(
            node_id=node_id,
            flow_node_type=node_type.value,
            position=position,
            name=node_name,
            data=node_config
        )
        
        self._nodes.append(node)
        return node_id
    
    def _calculate_position(self, node_type: FlowNodeTypeEnum) -> Position:
        """Calculate node position based on layout algorithm"""
        if not self._nodes:
            return Position(0, 0)
        
        if self.layout == LayoutAlgorithm.VERTICAL:
            # Find the rightmost x position
            max_x = max(n.position.x for n in self._nodes)
            
            # Find nodes at max_x to stack below
            nodes_at_edge = [n for n in self._nodes if n.position.x == max_x]
            max_y = max(n.position.y for n in nodes_at_edge)
            
            return Position(max_x, max_y + self.DEFAULT_NODE_SPACING_Y)
        
        elif self.layout == LayoutAlgorithm.HORIZONTAL:
            max_y = max(n.position.y for n in self._nodes)
            return Position(
                len(self._nodes) * self.DEFAULT_NODE_SPACING_X,
                max_y
            )
        
        # Auto layout
        return Position(
            (len(self._nodes) % 4) * self.DEFAULT_NODE_SPACING_X,
            (len(self._nodes) // 4) * self.DEFAULT_NODE_SPACING_Y
        )
    
    def connect(
        self,
        source_id: str,
        target_id: str,
        source_handle: str = "source",
        target_handle: str = "target"
    ) -> str:
        """
        Connect two nodes.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            source_handle: Source handle (default: "source")
            target_handle: Target handle (default: "target")
            
        Returns:
            Edge ID
        """
        # Validate nodes exist
        source_exists = any(n.node_id == source_id for n in self._nodes)
        target_exists = any(n.node_id == target_id for n in self._nodes)
        
        if not source_exists:
            raise ValueError(f"Source node {source_id} does not exist")
        if not target_exists:
            raise ValueError(f"Target node {target_id} does not exist")
        
        edge_id = self._generate_id("edge")
        
        edge = WorkflowEdge(
            edge_id=edge_id,
            source=source_id,
            target=target_id,
            source_handle=source_handle,
            target_handle=target_handle
        )
        
        self._edges.append(edge)
        return edge_id
    
    def connect_sequence(self, node_ids: List[str]) -> None:
        """Connect nodes in sequence"""
        for i in range(len(node_ids) - 1):
            self.connect(node_ids[i], node_ids[i + 1])
    
    def set_node_input(
        self,
        node_id: str,
        key: str,
        value: Any,
        value_type: WorkflowIOValueType = WorkflowIOValueType.REFERENCE
    ) -> None:
        """Set node input value"""
        node = next((n for n in self._nodes if n.node_id == node_id), None)
        if not node:
            raise ValueError(f"Node {node_id} does not exist")
        
        # Update data
        node.data[key] = value
        
        # Also add to inputs list if not exists
        if key not in [inp.key for inp in node.inputs]:
            node.inputs.append(FlowNodeInput(
                key=key,
                label=key,
                type=FlowNodeInputType.REFERENCE,
                value_type=value_type
            ))
    
    def set_node_config(self, node_id: str, config: Dict[str, Any]) -> None:
        """Update node configuration"""
        node = next((n for n in self._nodes if n.node_id == node_id), None)
        if not node:
            raise ValueError(f"Node {node_id} does not exist")
        
        node.data.update(config)
    
    def validate(self) -> WorkflowValidationResult:
        """Validate the workflow structure"""
        errors: List[WorkflowValidationError] = []
        warnings: List[str] = []
        
        # Check for nodes
        if not self._nodes:
            errors.append(WorkflowValidationError(
                code="NO_NODES",
                message="Workflow must have at least one node"
            ))
            return WorkflowValidationResult(is_valid=False, errors=errors)
        
        # Check for entry node
        if not self._entry_node:
            errors.append(WorkflowValidationError(
                code="NO_ENTRY",
                message="Workflow must have an entry node (workflowStart)"
            ))
        
        # Check for exit nodes
        if not self._exit_nodes:
            warnings.append("Workflow should have at least one exit node (answerNode)")
        
        # Check for orphan nodes
        connected_nodes: Dict[str, bool] = {n.node_id: False for n in self._nodes}
        
        for edge in self._edges:
            if edge.source in connected_nodes:
                connected_nodes[edge.source] = True
            if edge.target in connected_nodes:
                connected_nodes[edge.target] = True
        
        orphan_nodes = [nid for nid, connected in connected_nodes.items() if not connected]
        if orphan_nodes and len(self._nodes) > 1:
            warnings.append(f"Orphan nodes detected: {orphan_nodes}")
        
        # Check edge references
        node_ids = {n.node_id for n in self._nodes}
        
        for edge in self._edges:
            if edge.source not in node_ids:
                errors.append(WorkflowValidationError(
                    code="INVALID_EDGE_SOURCE",
                    message=f"Edge {edge.edge_id} references non-existent source node",
                    node_id=edge.edge_id
                ))
            if edge.target not in node_ids:
                errors.append(WorkflowValidationError(
                    code="INVALID_EDGE_TARGET",
                    message=f"Edge {edge.edge_id} references non-existent target node",
                    node_id=edge.edge_id
                ))
        
        # Check for cycles (simple detection)
        if self._has_cycle():
            warnings.append("Workflow contains potential cycles")
        
        return WorkflowValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _has_cycle(self) -> bool:
        """Check for cycles in the workflow graph"""
        if not self._edges:
            return False
        
        # Build adjacency list
        graph: Dict[str, List[str]] = {n.node_id: [] for n in self._nodes}
        for edge in self._edges:
            if edge.source in graph:
                graph[edge.source].append(edge.target)
        
        # DFS cycle detection
        visited: Dict[str, bool] = {n: False for n in graph}
        rec_stack: Dict[str, bool] = {n: False for n in graph}
        
        def dfs(node: str) -> bool:
            visited[node] = True
            rec_stack[node] = True
            
            for neighbor in graph.get(node, []):
                if not visited.get(neighbor, False):
                    if dfs(neighbor):
                        return True
                elif rec_stack.get(neighbor, False):
                    return True
            
            rec_stack[node] = False
            return False
        
        for node in graph:
            if not visited.get(node, False):
                if dfs(node):
                    return True
        
        return False
    
    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        """Get node by ID"""
        return next((n for n in self._nodes if n.node_id == node_id), None)
    
    def get_exit_node(self) -> Optional[str]:
        """Get the primary exit node (first answerNode)"""
        return self._exit_nodes[0] if self._exit_nodes else None
    
    def build(
        self,
        node_types: List[FlowNodeTypeEnum],
        connections: Optional[List[tuple]] = None,
        auto_connect: bool = True
    ) -> GeneratedWorkflow:
        """
        Build a workflow from node types.
        
        Args:
            node_types: List of node types to add
            connections: List of (source_idx, target_idx) connections
            auto_connect: Automatically connect nodes in sequence
            
        Returns:
            GeneratedWorkflow
        """
        # Add nodes
        node_ids = []
        for node_type in node_types:
            node_id = self.add_node(node_type)
            node_ids.append(node_id)
        
        # Connect nodes
        if auto_connect:
            self.connect_sequence(node_ids)
        elif connections:
            for src_idx, tgt_idx in connections:
                self.connect(node_ids[src_idx], node_ids[tgt_idx])
        
        # Validate
        validation = self.validate()
        
        return GeneratedWorkflow(
            nodes=self._nodes,
            edges=self._edges,
            validation=validation,
            metadata={
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
                "entry_node": self._entry_node,
                "exit_nodes": self._exit_nodes
            }
        )
    
    def export(self) -> Dict[str, Any]:
        """Export workflow to FastGPT format"""
        return {
            "nodes": [n.to_dict() for n in self._nodes],
            "edges": [e.to_dict() for e in self._edges]
        }
    
    def clear(self) -> None:
        """Clear all nodes and edges"""
        self._nodes.clear()
        self._edges.clear()
        self._node_counter = 0
        self._entry_node = None
        self._exit_nodes.clear()


# ============================================================
# Builder with Requirement Analysis
# ============================================================

class SmartWorkflowBuilder(WorkflowBuilder):
    """
    Enhanced workflow builder that integrates with ComponentRegistry
    for intelligent workflow generation from requirements.
    """
    
    def build_from_requirements(
        self,
        requirements: str,
        complexity: Optional[str] = None
    ) -> GeneratedWorkflow:
        """
        Build workflow by analyzing requirements.
        
        Args:
            requirements: Natural language requirements
            complexity: Optional complexity hint (simple/medium/complex)
            
        Returns:
            GeneratedWorkflow
        """
        # Analyze requirements
        analysis = self.registry.analyze_requirements(requirements)
        
        # Determine node types based on analysis and complexity
        node_types = self._determine_node_types(analysis, complexity)
        
        # Build workflow
        workflow = self.build(node_types)
        
        # Add analysis metadata
        workflow.metadata["analysis"] = {
            "confidence": analysis.confidence,
            "reasoning": analysis.reasoning,
            "needed_components": [n.value for n in analysis.needed_components],
            "missing_components": [
                {
                    "capability": m.required_capability,
                    "plugin_name": m.suggested_plugin_name
                }
                for m in analysis.missing_components
            ]
        }
        
        return workflow
    
    def _determine_node_types(
        self,
        analysis,
        complexity: Optional[str]
    ) -> List[FlowNodeTypeEnum]:
        """Determine node types from analysis result"""
        node_types = list(analysis.needed_components)
        
        # Always ensure entry and exit
        if FlowNodeTypeEnum.WORKFLOW_START not in node_types:
            node_types.insert(0, FlowNodeTypeEnum.WORKFLOW_START)
        
        if FlowNodeTypeEnum.ANSWER_NODE not in node_types:
            # Add answer node at the end
            node_types.append(FlowNodeTypeEnum.ANSWER_NODE)
        
        # Add AI node if needed (between entry and exit)
        has_ai = any(
            n in node_types for n in [
                FlowNodeTypeEnum.CHAT_NODE,
                FlowNodeTypeEnum.AGENT,
                FlowNodeTypeEnum.CLASSIFY_QUESTION
            ]
        )
        
        if not has_ai and FlowNodeTypeEnum.ANSWER_NODE in node_types:
            # Insert chat node before answer
            answer_idx = node_types.index(FlowNodeTypeEnum.ANSWER_NODE)
            if complexity != "simple":
                node_types.insert(answer_idx, FlowNodeTypeEnum.CHAT_NODE)
            else:
                node_types.insert(answer_idx, FlowNodeTypeEnum.CHAT_NODE)
        
        return node_types
