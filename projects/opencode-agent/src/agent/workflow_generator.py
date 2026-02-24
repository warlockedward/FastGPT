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
    """Generates valid FastGPT workflows from requirements using LLM"""
    
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or os.environ.get("VLLM_BASE_URL", os.environ.get("FASTGPT_API_URL", "http://fastgpt:3000"))
        self.api_key = api_key or os.environ.get("VLLM_API_KEY", os.environ.get("FASTGPT_API_KEY", ""))
        self.model = model or os.environ.get("VLLM_MODEL", "Qwen3-235B-A22B-Thinking-2507")
        self.client = httpx.AsyncClient(timeout=120.0)
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
        }
    
    def _get_node_template(self, node_type: str) -> Dict[str, Any]:
        """Get the proper inputs/outputs for each node type based on FastGPT templates"""
        
        templates = {
            FlowNodeType.WORKFLOW_START.value: {
                "name": "Workflow Start",
                "inputs": [
                    {"key": "userChatInput", "renderTypeList": ["reference", "input"], "label": "User Input", "valueType": "string", "required": True}
                ],
                "outputs": [
                    {"key": "userChatInput", "renderTypeList": ["hidden"], "label": "User Input", "valueType": "string"}
                ]
            },
            FlowNodeType.CHAT_NODE.value: {
                "name": "AI Chat",
                "inputs": [
                    {"key": "systemPrompt", "renderTypeList": ["textarea"], "label": "System Prompt", "valueType": "string", "value": "You are a helpful AI assistant."},
                    {"key": "history", "renderTypeList": ["reference", "hidden"], "label": "History", "valueType": "array", "value": []},
                    {"key": "userChatInput", "renderTypeList": ["reference", "input"], "label": "User Question", "valueType": "string", "required": True},
                    {"key": "settingAiModel", "renderTypeList": ["selectLLMModel"], "label": "AI Model", "valueType": "string"}
                ],
                "outputs": [
                    {"key": "responseText", "renderTypeList": ["hidden"], "label": "AI Response", "valueType": "string"},
                    {"key": "history", "renderTypeList": ["hidden"], "label": "History", "valueType": "array"}
                ]
            },
            FlowNodeType.ANSWER_NODE.value: {
                "name": "Answer",
                "inputs": [
                    {"key": "responseText", "renderTypeList": ["reference", "textarea"], "label": "Response Content", "valueType": "string", "required": True}
                ],
                "outputs": [
                    {"key": "answerText", "renderTypeList": ["hidden"], "label": "Response", "valueType": "string"}
                ]
            },
            FlowNodeType.DATASET_SEARCH.value: {
                "name": "Knowledge Base Search",
                "inputs": [
                    {"key": "userChatInput", "renderTypeList": ["reference", "input"], "label": "User Question", "valueType": "string", "required": True},
                    {"key": "datasets", "renderTypeList": ["selectDataset"], "label": "Select Knowledge Base", "valueType": "array"},
                    {"key": "similarity", "renderTypeList": ["numberInput"], "label": "Similarity Threshold", "valueType": "number", "value": 0.7},
                    {"key": "limit", "renderTypeList": ["numberInput"], "label": "Max Results", "valueType": "number", "value": 5}
                ],
                "outputs": [
                    {"key": "quoteList", "renderTypeList": ["hidden"], "label": "Search Results", "valueType": "array"}
                ]
            },
            FlowNodeType.IF_ELSE.value: {
                "name": "Conditional",
                "inputs": [
                    {"key": "condition", "renderTypeList": ["input"], "label": "Condition", "valueType": "string", "required": True}
                ],
                "outputs": [
                    {"key": "true", "renderTypeList": ["hidden"], "label": "True Branch", "valueType": "string"},
                    {"key": "false", "renderTypeList": ["hidden"], "label": "False Branch", "valueType": "string"}
                ]
            },
            FlowNodeType.HTTP_REQUEST.value: {
                "name": "HTTP Request",
                "inputs": [
                    {"key": "url", "renderTypeList": ["input"], "label": "Request URL", "valueType": "string", "required": True},
                    {"key": "method", "renderTypeList": ["select"], "label": "Method", "valueType": "string", "value": "GET"},
                    {"key": "headers", "renderTypeList": ["json"], "label": "Headers", "valueType": "object"},
                    {"key": "body", "renderTypeList": ["json"], "label": "Request Body", "valueType": "object"}
                ],
                "outputs": [
                    {"key": "response", "renderTypeList": ["hidden"], "label": "Response", "valueType": "object"}
                ]
            },
            FlowNodeType.CODE.value: {
                "name": "Code",
                "inputs": [
                    {"key": "code", "renderTypeList": ["JSONEditor"], "label": "Code", "valueType": "string", "value": "const result = input;\nreturn result;"},
                    {"key": "inputVariables", "renderTypeList": ["reference"], "label": "Input Variables", "valueType": "array"}
                ],
                "outputs": [
                    {"key": "output", "renderTypeList": ["hidden"], "label": "Output", "valueType": "string"}
                ]
            },
            FlowNodeType.CLASSIFY_QUESTION.value: {
                "name": "Intent Classification",
                "inputs": [
                    {"key": "userChatInput", "renderTypeList": ["reference", "input"], "label": "User Question", "valueType": "string", "required": True},
                    {"key": "classes", "renderTypeList": ["input"], "label": "Classification Labels", "valueType": "string", "value": "Intent 1\nIntent 2\nIntent 3"}
                ],
                "outputs": [
                    {"key": "selectedClassIndex", "renderTypeList": ["hidden"], "label": "Selected Index", "valueType": "number"}
                ]
            },
            FlowNodeType.CONTENT_EXTRACT.value: {
                "name": "Content Extract",
                "inputs": [
                    {"key": "content", "renderTypeList": ["reference", "textarea"], "label": "Content", "valueType": "string", "required": True},
                    {"key": "instruction", "renderTypeList": ["input", "textarea"], "label": "Extraction Instruction", "valueType": "string"}
                ],
                "outputs": [
                    {"key": "extractedFields", "renderTypeList": ["hidden"], "label": "Extracted Data", "valueType": "object"}
                ]
            },
            FlowNodeType.AGENT.value: {
                "name": "AI Agent",
                "inputs": [
                    {"key": "systemPrompt", "renderTypeList": ["textarea"], "label": "System Prompt", "valueType": "string", "value": "You are an AI agent."},
                    {"key": "userChatInput", "renderTypeList": ["reference", "input"], "label": "User Input", "valueType": "string"}
                ],
                "outputs": [
                    {"key": "responseText", "renderTypeList": ["hidden"], "label": "Response", "valueType": "string"}
                ]
            }
        }
        
        return templates.get(node_type, {"name": node_type, "inputs": [], "outputs": []})
    
    def _build_system_prompt(
        self,
        available_plugins: List[Dict[str, Any]],
        node_types: List[Dict[str, Any]],
        categories: List[Dict[str, Any]]
    ) -> str:
        prompt_parts = [
            "You are an AI Workflow generator for FastGPT. Generate a valid FastGPT workflow JSON based on user requirements.",
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
                "Available installed plugins (tools) that can be used:"
            ])
            for plugin in available_plugins:
                name = plugin.get("name", "Unknown")
                desc = plugin.get("description", "")
                flow_type = plugin.get("flowNodeType", "tool")
                prompt_parts.append(f"- {name}: {desc} [type: {flow_type}]")
        
        prompt_parts.extend([
            "",
            "IMPORTANT OUTPUT FORMAT:",
            "Respond ONLY with a valid JSON object, no other text. Use this exact structure:",
            "{",
            '  "nodes": [',
            '    {"nodeId": "unique_id", "flowNodeType": "node_type", "name": "Node Name", "x": 0, "y": 0},',
            '    ...',
            '  ],',
            '  "edges": [',
            '    {"source": "source_id", "sourceHandle": "out", "target": "target_id", "targetHandle": "in"},',
            '    ...',
            '  ]',
            "}",
            "",
            "Requirements:",
            "1. workflowStart must be the entry point (first node)",
            "2. The flow must end at answerNode or similar output node",
            "3. Each node must have a unique nodeId",
            "4. Edges must connect nodes in logical order",
            "5. Use appropriate x, y coordinates for visual layout (x: 250-1000, y: 0-800)",
            "6. Consider the user's requirements and select appropriate nodes",
            "7. Output ONLY valid JSON, no explanations or markdown"
        ])
        
        return "\n".join(prompt_parts)
    
    def _generate_id(self) -> str:
        return f"node_{uuid.uuid4().hex[:8]}"
    
    async def _call_llm(self, system_prompt: str, user_message: str) -> Dict[str, Any]:
        """Call vLLM API to generate workflow"""
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        response = await self.client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = content[json_start:json_end]
            return json.loads(json_str)
        
        raise ValueError("No valid JSON found in LLM response")
    
    def _parse_llm_response(self, llm_result: Dict[str, Any]) -> tuple:
        """Parse LLM response into nodes and edges"""
        nodes = []
        edges = []
        
        for node_data in llm_result.get("nodes", []):
            node_id = node_data.get("nodeId", self._generate_id())
            flow_type = node_data.get("flowNodeType", "chatNode")
            name = node_data.get("name", "Node")
            x = node_data.get("x", 250)
            y = node_data.get("y", 0)
            
            # Get proper template with inputs/outputs
            template = self._get_node_template(flow_type)
            
            nodes.append(WorkflowNode(
                nodeId=node_id,
                flowNodeType=flow_type,
                name=name,
                position=Position(x=x, y=y),
                inputs=template.get("inputs", []),
                outputs=template.get("outputs", [])
            ))
        
        for edge_data in llm_result.get("edges", []):
            edges.append(WorkflowEdge(
                source=edge_data.get("source", ""),
                sourceHandle=edge_data.get("sourceHandle", "out"),
                target=edge_data.get("target", ""),
                targetHandle=edge_data.get("targetHandle", "in")
            ))
        
        return nodes, edges
    
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
        
        # Get template with inputs/outputs
        template = self._get_node_template(node_type)
        node_name = template.get("name", name_map.get(node_type, node_type))
        inputs = template.get("inputs", [])
        outputs = template.get("outputs", [])
        
        x = 250
        y = index * 200
        
        return WorkflowNode(
            nodeId=node_id,
            flowNodeType=node_type,
            name=node_name,
            position=Position(x=x, y=y),
            inputs=inputs,
            outputs=outputs
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
            
            user_message = f"""Generate a FastGPT workflow for the following requirement:

{requirements}

Intent: {intent}
Complexity: {complexity}

Please generate the workflow JSON now."""
            
            try:
                llm_result = await self._call_llm(system_prompt, user_message)
                nodes, edges = self._parse_llm_response(llm_result)
                
                if nodes and edges:
                    return WorkflowResult(nodes=nodes, edges=edges)
                
            except Exception as e:
                pass
            
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
