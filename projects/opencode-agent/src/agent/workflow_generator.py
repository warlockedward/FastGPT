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
    
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or os.environ.get("FASTGPT_API_URL", "http://fastgpt:3000")
        self.api_key = api_key or os.environ.get("FASTGPT_API_KEY", "")
        self.client = httpx.AsyncClient(timeout=30.0)
        self._node_type_metadata = self._build_node_type_metadata()
    
    def _build_node_type_metadata(self) -> Dict[str, Dict[str, str]]:
        return {
            "workflowStart": {"label": "开始", "category": "core", "description": "工作流入口节点"},
            "chatNode": {"label": "AI 对话", "category": "ai", "description": "AI 对话节点，支持多种模型"},
            "answerNode": {"label": "直接回复", "category": "output", "description": "直接返回内容给用户"},
            "datasetSearchNode": {"label": "知识库搜索", "category": "dataset", "description": "从知识库检索相关内容"},
            "datasetConcatNode": {"label": "知识库拼接", "category": "dataset", "description": "拼接多个知识库检索结果"},
            "classifyQuestion": {"label": "意图分类", "category": "ai", "description": "根据用户输入分类意图"},
            "contentExtract": {"label": "内容提取", "category": "ai", "description": "从文本中提取结构化数据"},
            "httpRequest468": {"label": "HTTP 请求", "category": "integration", "description": "发起 HTTP API 请求"},
            "ifElseNode": {"label": "条件分支", "category": "control", "description": "根据条件执行不同分支"},
            "agent": {"label": "AI Agent", "category": "ai", "description": "具有规划能力的 AI Agent"},
            "toolCall": {"label": "工具调用", "category": "integration", "description": "调用外部工具"},
            "code": {"label": "代码执行", "category": "tool", "description": "执行自定义代码"},
            "variableUpdate": {"label": "变量更新", "category": "variable", "description": "更新工作流变量"},
            "globalVariable": {"label": "全局变量", "category": "variable", "description": "定义全局变量"},
            "userSelect": {"label": "用户选择", "category": "input", "description": "让用户从选项中选择"},
            "formInput": {"label": "表单输入", "category": "input", "description": "用户表单输入"},
            "readFiles": {"label": "读取文件", "category": "tool", "description": "读取上传的文件"},
            "loop": {"label": "循环", "category": "control", "description": "循环执行节点"},
            "loopStart": {"label": "循环开始", "category": "control", "description": "循环开始节点"},
            "loopEnd": {"label": "循环结束", "category": "control", "description": "循环结束节点"},
            "pluginInput": {"label": "插件输入", "category": "plugin", "description": "插件输入参数"},
            "pluginOutput": {"label": "插件输出", "category": "plugin", "description": "插件输出参数"},
            "textEditor": {"label": "文本编辑", "category": "tool", "description": "富文本编辑器"},
            "queryExtension": {"label": "查询扩展", "category": "ai", "description": "扩展用户查询"},
            "tool": {"label": "工具", "category": "integration", "description": "调用已安装的工具"},
            "toolSet": {"label": "工具集", "category": "integration", "description": "工具集合"},
            "appModule": {"label": "应用模块", "category": "integration", "description": "调用其他应用"},
            "pluginModule": {"label": "插件模块", "category": "plugin", "description": "调用插件"}
        }
    
    def _build_system_prompt(
        self,
        available_plugins: List[Dict[str, Any]],
        node_types: List[Dict[str, Any]],
        categories: List[Dict[str, Any]]
    ) -> str:
        prompt_parts = [
            "You are an AI Workflow generator. Generate a valid FastGPT workflow based on user requirements.",
            "",
            "Available node types:"
        ]
        
        if node_types:
            for node in node_types:
                node_id = node.get("id", "")
                metadata = node.get("label", node_id)
                category = node.get("category", "")
                desc = node.get("description", "")
                prompt_parts.append(f"- {node_id}: {metadata} ({category}) - {desc}")
        else:
            for node_id, meta in self._node_type_metadata.items():
                prompt_parts.append(f"- {node_id}: {meta['label']} ({meta['category']}) - {meta['description']}")
        
        if available_plugins:
            prompt_parts.extend([
                "",
                "Available installed plugins (tools):"
            ])
            for plugin in available_plugins:
                name = plugin.get("name", "Unknown")
                desc = plugin.get("description", "")
                flow_type = plugin.get("flowNodeType", "tool")
                prompt_parts.append(f"- {name}: {desc} [type: {flow_type}]")
        
        if categories:
            prompt_parts.extend([
                "",
                "Node categories:"
            ])
            for cat in categories:
                cat_id = cat.get("id", "")
                cat_label = cat.get("label", cat_id)
                prompt_parts.append(f"- {cat_id}: {cat_label}")
        
        prompt_parts.extend([
            "",
            "Respond with a JSON object:",
            '{',
            '  "nodes": [',
            '    {"nodeId": "unique_id", "flowNodeType": "node_type", "name": "Node Name"}',
            '  ],',
            '  "edges": [',
            '    {"source": "source_id", "sourceHandle": "out", "target": "target_id", "targetHandle": "in"}',
            '  ]',
            '}',
            "",
            "Ensure:",
            "1. workflowStart is the entry point",
            "2. answerNode is the final output",
            "3. Edges connect nodes in logical flow",
            "4. Each node has unique ID"
        ])
        
        return "\n".join(prompt_parts)
    
    def _generate_id(self) -> str:
        return f"node_{uuid.uuid4().hex[:8]}"
    
    def _get_nodes_for_complexity(self, complexity: str, requirements: str) -> List[str]:
        requirements_lower = requirements.lower()
        
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
        
        x = 250
        y = index * 200
        
        return WorkflowNode(
            nodeId=node_id,
            flowNodeType=node_type,
            name=name_map.get(node_type, node_type),
            position=Position(x=x, y=y),
            inputs=[],
            outputs=[]
        )
    
    def _create_edges(self, nodes: List[WorkflowNode]) -> List[WorkflowEdge]:
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
        requirements: str,
        available_plugins: Optional[List[Dict[str, Any]]] = None,
        node_types: Optional[List[Dict[str, Any]]] = None,
        categories: Optional[List[Dict[str, Any]]] = None
    ) -> WorkflowResult:
        try:
            if available_plugins is None:
                available_plugins = []
            if node_types is None:
                node_types = []
            if categories is None:
                categories = []
            
            system_prompt = self._build_system_prompt(
                available_plugins,
                node_types,
                categories
            )
            
            node_types_list = self._get_nodes_for_complexity(complexity, requirements)
            
            nodes = []
            for i, node_type in enumerate(node_types_list):
                node_id = self._generate_id()
                node = self._create_node(node_type.value, node_id, i, len(node_types_list))
                nodes.append(node)
            
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
        errors = []
        warnings = []
        
        if not nodes:
            errors.append("Workflow must have at least one node")
            return ValidationResult(is_valid=False, errors=errors)
        
        node_types = [n.get("flowNodeType") for n in nodes]
        if FlowNodeType.WORKFLOW_START.value not in node_types:
            errors.append("Workflow must have a workflowStart node")
        
        if FlowNodeType.ANSWER_NODE.value not in node_types:
            warnings.append("Workflow should have an answerNode as final output")
        
        node_ids = set(n.get("nodeId") for n in nodes)
        
        connected_nodes = set()
        for edge in edges:
            connected_nodes.add(edge.get("source"))
            connected_nodes.add(edge.get("target"))
        
        orphan_nodes = node_ids - connected_nodes
        if orphan_nodes and len(nodes) > 1:
            warnings.append(f"Orphan nodes detected (not connected): {orphan_nodes}")
        
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
        await self.client.aclose()
