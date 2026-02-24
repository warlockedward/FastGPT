"""
ComponentRegistry - Discovers and manages FastGPT workflow components

This module provides:
1. Discovery of all available workflow node types
2. Loading of node templates and configurations
3. Analysis of user requirements to identify needed components
4. Detection of missing components that need custom plugins
"""
from __future__ import annotations
import os
from enum import Enum
from typing import Optional, Dict, List, Any, Set
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import httpx


class FlowNodeTypeEnum(str, Enum):
    """FastGPT workflow node types - complete list from FlowNodeTypeEnum"""
    # Core nodes
    WORKFLOW_START = "workflowStart"
    CHAT_NODE = "chatNode"
    ANSWER_NODE = "answerNode"
    
    # Dataset nodes
    DATASET_SEARCH_NODE = "datasetSearchNode"
    DATASET_CONCAT_NODE = "datasetConcatNode"
    
    # AI nodes
    CLASSIFY_QUESTION = "classifyQuestion"
    CONTENT_EXTRACT = "contentExtract"
    AGENT = "agent"
    TOOL_CALL = "tools"
    QUERY_EXTENSION = "cfr"
    
    # Control flow
    IF_ELSE_NODE = "ifElseNode"
    LOOP = "loop"
    LOOP_START = "loopStart"
    LOOP_END = "loopEnd"
    
    # HTTP & Code
    HTTP_REQUEST = "httpRequest468"
    CODE = "code"
    TEXT_EDITOR = "textEditor"
    
    # Variables
    VARIABLE_UPDATE = "variableUpdate"
    GLOBAL_VARIABLE = "globalVariable"
    
    # I/O
    USER_SELECT = "userSelect"
    FORM_INPUT = "formInput"
    
    # Files
    READ_FILES = "readFiles"
    
    # System
    PLUGIN_INPUT = "pluginInput"
    PLUGIN_OUTPUT = "pluginOutput"
    PLUGIN_MODULE = "pluginModule"
    APP_MODULE = "appModule"
    TOOL = "tool"
    TOOL_SET = "toolSet"
    LAF_MODULE = "lafModule"
    CUSTOM_FEEDBACK = "customFeedback"
    
    # Deprecated
    RUN_APP = "app"


class NodeCategory(str, Enum):
    """Category of node"""
    CORE = "core"
    DATASET = "dataset"
    AI = "ai"
    CONTROL = "control"
    HTTP_CODE = "http_code"
    VARIABLE = "variable"
    INTERACTIVE = "interactive"
    FILE = "file"
    PLUGIN = "plugin"
    SYSTEM = "system"


@dataclass
class NodeMetadata:
    """Metadata for a workflow node type"""
    type: FlowNodeTypeEnum
    name: str
    description: str
    category: NodeCategory
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    required_params: List[str] = field(default_factory=list)
    is_entry: bool = False
    is_exit: bool = False


@dataclass
class PluginMetadata:
    """Metadata for a plugin"""
    plugin_id: str
    name: str
    description: str
    version: str
    inputs: List[Dict[str, Any]]
    outputs: List[Dict[str, Any]]
    is_installed: bool = False
    team_id: Optional[str] = None


@dataclass 
class ToolMetadata:
    """Metadata for a tool"""
    tool_id: str
    name: str
    description: str
    type: str  # http, function, etc.
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComponentCapability:
    """A capability that a component can provide"""
    keyword: str  # keyword to match in requirements
    node_types: List[FlowNodeTypeEnum]
    description: str
    priority: int = 1


@dataclass
class MissingComponent:
    """A component that is needed but not available"""
    required_capability: str
    suggested_plugin_name: str
    suggested_description: str
    required_inputs: List[Dict[str, Any]]
    required_outputs: List[Dict[str, Any]]


@dataclass
class RequirementAnalysisResult:
    """Result of analyzing user requirements"""
    needed_components: List[FlowNodeTypeEnum]
    missing_components: List[MissingComponent]
    confidence: float
    reasoning: List[str]


class ComponentRegistry:
    """
    Registry for discovering and managing FastGPT components.
    
    Provides:
    - Static node type definitions from FastGPT enum
    - Dynamic plugin/tool loading from FastGPT API
    - Requirement analysis to identify needed components
    """
    
    # Node type to category mapping
    NODE_CATEGORIES: Dict[FlowNodeTypeEnum, NodeCategory] = {
        FlowNodeTypeEnum.WORKFLOW_START: NodeCategory.CORE,
        FlowNodeTypeEnum.CHAT_NODE: NodeCategory.AI,
        FlowNodeTypeEnum.ANSWER_NODE: NodeCategory.CORE,
        FlowNodeTypeEnum.DATASET_SEARCH_NODE: NodeCategory.DATASET,
        FlowNodeTypeEnum.DATASET_CONCAT_NODE: NodeCategory.DATASET,
        FlowNodeTypeEnum.CLASSIFY_QUESTION: NodeCategory.AI,
        FlowNodeTypeEnum.CONTENT_EXTRACT: NodeCategory.AI,
        FlowNodeTypeEnum.AGENT: NodeCategory.AI,
        FlowNodeTypeEnum.TOOL_CALL: NodeCategory.AI,
        FlowNodeTypeEnum.QUERY_EXTENSION: NodeCategory.AI,
        FlowNodeTypeEnum.IF_ELSE_NODE: NodeCategory.CONTROL,
        FlowNodeTypeEnum.LOOP: NodeCategory.CONTROL,
        FlowNodeTypeEnum.LOOP_START: NodeCategory.CONTROL,
        FlowNodeTypeEnum.LOOP_END: NodeCategory.CONTROL,
        FlowNodeTypeEnum.HTTP_REQUEST: NodeCategory.HTTP_CODE,
        FlowNodeTypeEnum.CODE: NodeCategory.HTTP_CODE,
        FlowNodeTypeEnum.TEXT_EDITOR: NodeCategory.HTTP_CODE,
        FlowNodeTypeEnum.VARIABLE_UPDATE: NodeCategory.VARIABLE,
        FlowNodeTypeEnum.GLOBAL_VARIABLE: NodeCategory.VARIABLE,
        FlowNodeTypeEnum.USER_SELECT: NodeCategory.INTERACTIVE,
        FlowNodeTypeEnum.FORM_INPUT: NodeCategory.INTERACTIVE,
        FlowNodeTypeEnum.READ_FILES: NodeCategory.FILE,
        FlowNodeTypeEnum.PLUGIN_INPUT: NodeCategory.PLUGIN,
        FlowNodeTypeEnum.PLUGIN_OUTPUT: NodeCategory.PLUGIN,
        FlowNodeTypeEnum.PLUGIN_MODULE: NodeCategory.PLUGIN,
        FlowNodeTypeEnum.APP_MODULE: NodeCategory.PLUGIN,
        FlowNodeTypeEnum.TOOL: NodeCategory.PLUGIN,
        FlowNodeTypeEnum.TOOL_SET: NodeCategory.PLUGIN,
        FlowNodeTypeEnum.LAF_MODULE: NodeCategory.PLUGIN,
        FlowNodeTypeEnum.CUSTOM_FEEDBACK: NodeCategory.SYSTEM,
    }
    
    # Node names and descriptions
    NODE_INFO: Dict[FlowNodeTypeEnum, Dict[str, str]] = {
        FlowNodeTypeEnum.WORKFLOW_START: {
            "name": "Workflow Start",
            "description": "Entry point for workflow execution"
        },
        FlowNodeTypeEnum.CHAT_NODE: {
            "name": "AI Chat",
            "description": "AI model for processing user messages"
        },
        FlowNodeTypeEnum.ANSWER_NODE: {
            "name": "Answer",
            "description": "Output node for final response"
        },
        FlowNodeTypeEnum.DATASET_SEARCH_NODE: {
            "name": "Knowledge Base Search",
            "description": "Search knowledge base for relevant content"
        },
        FlowNodeTypeEnum.DATASET_CONCAT_NODE: {
            "name": "Knowledge Base Concat",
            "description": "Concatenate results from multiple datasets"
        },
        FlowNodeTypeEnum.CLASSIFY_QUESTION: {
            "name": "Intent Classification",
            "description": "Classify user intent or question type"
        },
        FlowNodeTypeEnum.CONTENT_EXTRACT: {
            "name": "Content Extract",
            "description": "Extract structured data from unstructured content"
        },
        FlowNodeTypeEnum.AGENT: {
            "name": "AI Agent",
            "description": "AI agent with planning and tool use capabilities"
        },
        FlowNodeTypeEnum.TOOL_CALL: {
            "name": "Tool Call",
            "description": "Call external tools or functions"
        },
        FlowNodeTypeEnum.IF_ELSE_NODE: {
            "name": "Conditional",
            "description": "Branch based on conditions"
        },
        FlowNodeTypeEnum.LOOP: {
            "name": "Loop",
            "description": "Loop over a collection of items"
        },
        FlowNodeTypeEnum.HTTP_REQUEST: {
            "name": "HTTP Request",
            "description": "Make HTTP requests to external APIs"
        },
        FlowNodeTypeEnum.CODE: {
            "name": "Code",
            "description": "Execute custom code"
        },
        FlowNodeTypeEnum.TEXT_EDITOR: {
            "name": "Text Editor",
            "description": "Process and transform text"
        },
        FlowNodeTypeEnum.VARIABLE_UPDATE: {
            "name": "Variable Update",
            "description": "Update workflow variables"
        },
        FlowNodeTypeEnum.USER_SELECT: {
            "name": "User Select",
            "description": "Present options for user to select"
        },
        FlowNodeTypeEnum.FORM_INPUT: {
            "name": "Form Input",
            "description": "Collect form input from user"
        },
        FlowNodeTypeEnum.READ_FILES: {
            "name": "Read Files",
            "description": "Read content from files"
        },
        FlowNodeTypeEnum.PLUGIN_MODULE: {
            "name": "Plugin Module",
            "description": "Use a plugin in the workflow"
        },
        FlowNodeTypeEnum.APP_MODULE: {
            "name": "App Module",
            "description": "Use another app as a module"
        },
    }
    
    # Capability keywords - maps natural language to node types
    CAPABILITIES: List[ComponentCapability] = [
        # Knowledge base / RAG
        ComponentCapability(
            keyword="知识库",
            node_types=[FlowNodeTypeEnum.DATASET_SEARCH_NODE],
            description="Knowledge base search",
            priority=10
        ),
        ComponentCapability(
            keyword="knowledge base",
            node_types=[FlowNodeTypeEnum.DATASET_SEARCH_NODE],
            description="Knowledge base search",
            priority=10
        ),
        ComponentCapability(
            keyword="search",
            node_types=[FlowNodeTypeEnum.DATASET_SEARCH_NODE],
            description="Search content",
            priority=5
        ),
        ComponentCapability(
            keyword="rag",
            node_types=[FlowNodeTypeEnum.DATASET_SEARCH_NODE, FlowNodeTypeEnum.DATASET_CONCAT_NODE],
            description="RAG retrieval",
            priority=10
        ),
        
        # Conditionals
        ComponentCapability(
            keyword="if",
            node_types=[FlowNodeTypeEnum.IF_ELSE_NODE],
            description="Conditional branching",
            priority=8
        ),
        ComponentCapability(
            keyword="如果",
            node_types=[FlowNodeTypeEnum.IF_ELSE_NODE],
            description="Conditional branching",
            priority=8
        ),
        ComponentCapability(
            keyword="check",
            node_types=[FlowNodeTypeEnum.IF_ELSE_NODE],
            description="Check conditions",
            priority=6
        ),
        ComponentCapability(
            keyword="验证",
            node_types=[FlowNodeTypeEnum.IF_ELSE_NODE],
            description="Verify conditions",
            priority=6
        ),
        
        # HTTP/API calls
        ComponentCapability(
            keyword="api",
            node_types=[FlowNodeTypeEnum.HTTP_REQUEST],
            description="Make API calls",
            priority=10
        ),
        ComponentCapability(
            keyword="http",
            node_types=[FlowNodeTypeEnum.HTTP_REQUEST],
            description="HTTP requests",
            priority=10
        ),
        ComponentCapability(
            keyword="请求",
            node_types=[FlowNodeTypeEnum.HTTP_REQUEST],
            description="Make requests",
            priority=8
        ),
        ComponentCapability(
            keyword="调用",
            node_types=[FlowNodeTypeEnum.TOOL_CALL, FlowNodeTypeEnum.AGENT],
            description="Call external services",
            priority=7
        ),
        
        # Custom code
        ComponentCapability(
            keyword="code",
            node_types=[FlowNodeTypeEnum.CODE],
            description="Execute custom code",
            priority=8
        ),
        ComponentCapability(
            keyword="代码",
            node_types=[FlowNodeTypeEnum.CODE],
            description="Execute custom code",
            priority=8
        ),
        ComponentCapability(
            keyword="process",
            node_types=[FlowNodeTypeEnum.CODE, FlowNodeTypeEnum.TEXT_EDITOR],
            description="Process data",
            priority=5
        ),
        
        # User interaction
        ComponentCapability(
            keyword="select",
            node_types=[FlowNodeTypeEnum.USER_SELECT],
            description="User selection",
            priority=7
        ),
        ComponentCapability(
            keyword="选择",
            node_types=[FlowNodeTypeEnum.USER_SELECT],
            description="User selection",
            priority=7
        ),
        ComponentCapability(
            keyword="form",
            node_types=[FlowNodeTypeEnum.FORM_INPUT],
            description="Form input",
            priority=6
        ),
        ComponentCapability(
            keyword="表单",
            node_types=[FlowNodeTypeEnum.FORM_INPUT],
            description="Form input",
            priority=6
        ),
        
        # Classification
        ComponentCapability(
            keyword="classify",
            node_types=[FlowNodeTypeEnum.CLASSIFY_QUESTION],
            description="Classify intent",
            priority=8
        ),
        ComponentCapability(
            keyword="分类",
            node_types=[FlowNodeTypeEnum.CLASSIFY_QUESTION],
            description="Classify intent",
            priority=8
        ),
        ComponentCapability(
            keyword="intent",
            node_types=[FlowNodeTypeEnum.CLASSIFY_QUESTION],
            description="Identify intent",
            priority=8
        ),
        
        # Extract
        ComponentCapability(
            keyword="extract",
            node_types=[FlowNodeTypeEnum.CONTENT_EXTRACT],
            description="Extract structured data",
            priority=7
        ),
        ComponentCapability(
            keyword="提取",
            node_types=[FlowNodeTypeEnum.CONTENT_EXTRACT],
            description="Extract structured data",
            priority=7
        ),
        
        # Loop
        ComponentCapability(
            keyword="loop",
            node_types=[FlowNodeTypeEnum.LOOP],
            description="Loop over items",
            priority=6
        ),
        ComponentCapability(
            keyword="循环",
            node_types=[FlowNodeTypeEnum.LOOP],
            description="Loop over items",
            priority=6
        ),
        
        # Agent
        ComponentCapability(
            keyword="agent",
            node_types=[FlowNodeTypeEnum.AGENT],
            description="AI agent with planning",
            priority=8
        ),
        ComponentCapability(
            keyword="智能体",
            node_types=[FlowNodeTypeEnum.AGENT],
            description="AI agent",
            priority=8
        ),
        
        # Files
        ComponentCapability(
            keyword="file",
            node_types=[FlowNodeTypeEnum.READ_FILES],
            description="Read files",
            priority=5
        ),
        ComponentCapability(
            keyword="文件",
            node_types=[FlowNodeTypeEnum.READ_FILES],
            description="Read files",
            priority=5
        ),
        
        # Notification
        ComponentCapability(
            keyword="notification",
            node_types=[FlowNodeTypeEnum.HTTP_REQUEST],
            description="Send notifications",
            priority=6
        ),
        ComponentCapability(
            keyword="notify",
            node_types=[FlowNodeTypeEnum.HTTP_REQUEST],
            description="Send notifications",
            priority=6
        ),
        ComponentCapability(
            keyword="通知",
            node_types=[FlowNodeTypeEnum.HTTP_REQUEST],
            description="Send notifications",
            priority=6
        ),
        ComponentCapability(
            keyword="webhook",
            node_types=[FlowNodeTypeEnum.HTTP_REQUEST],
            description="Webhook calls",
            priority=8
        ),
    ]
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        team_id: Optional[str] = None
    ):
        self.base_url = base_url or os.environ.get("FASTGPT_API_URL", "http://fastgpt:3000")
        self.api_key = api_key or os.environ.get("FASTGPT_API_KEY", "")
        self.team_id = team_id or os.environ.get("FASTGPT_TEAM_ID", "")
        
        # Initialize HTTP client
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0
        )
        
        # Cache for plugins and tools
        self._plugins: Dict[str, PluginMetadata] = {}
        self._tools: Dict[str, ToolMetadata] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize registry by loading plugins and tools"""
        if self._initialized:
            return
        
        # Load plugins from API
        await self._load_plugins()
        
        # Load tools from API
        await self._load_tools()
        
        self._initialized = True
    
    async def _load_plugins(self) -> None:
        """Load installed plugins from FastGPT API"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/team/plugin/list",
                json={"teamId": self.team_id}
            )
            if response.status_code == 200:
                data = response.json()
                for plugin in data.get("data", []):
                    self._plugins[plugin["id"]] = PluginMetadata(
                        plugin_id=plugin["id"],
                        name=plugin.get("name", ""),
                        description=plugin.get("description", ""),
                        version=plugin.get("version", "1.0.0"),
                        inputs=plugin.get("inputs", []),
                        outputs=plugin.get("outputs", []),
                        is_installed=True,
                        team_id=self.team_id
                    )
        except Exception as e:
            # If API fails, continue with empty plugins
            pass
    
    async def _load_tools(self) -> None:
        """Load available tools from FastGPT API"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/core/app/tool/getSystemToolTemplates",
                json={"teamId": self.team_id}
            )
            if response.status_code == 200:
                data = response.json()
                for tool in data.get("data", []):
                    self._tools[tool["id"]] = ToolMetadata(
                        tool_id=tool["id"],
                        name=tool.get("name", ""),
                        description=tool.get("description", ""),
                        type=tool.get("type", "http"),
                        parameters=tool.get("parameters", {})
                    )
        except Exception as e:
            # If API fails, continue with empty tools
            pass
    
    def get_all_node_types(self) -> List[FlowNodeTypeEnum]:
        """Get all available node types"""
        return list(FlowNodeTypeEnum)
    
    def get_node_metadata(self, node_type: FlowNodeTypeEnum) -> NodeMetadata:
        """Get metadata for a specific node type"""
        info = self.NODE_INFO.get(node_type, {"name": node_type.value, "description": ""})
        category = self.NODE_CATEGORIES.get(node_type, NodeCategory.SYSTEM)
        
        return NodeMetadata(
            type=node_type,
            name=info["name"],
            description=info["description"],
            category=category,
            is_entry=node_type == FlowNodeTypeEnum.WORKFLOW_START,
            is_exit=node_type == FlowNodeTypeEnum.ANSWER_NODE
        )
    
    def get_all_node_metadata(self) -> Dict[FlowNodeTypeEnum, NodeMetadata]:
        """Get metadata for all node types"""
        return {
            node_type: self.get_node_metadata(node_type)
            for node_type in FlowNodeTypeEnum
        }
    
    def get_plugins(self) -> Dict[str, PluginMetadata]:
        """Get all installed plugins"""
        return self._plugins.copy()
    
    def get_tools(self) -> Dict[str, ToolMetadata]:
        """Get all available tools"""
        return self._tools.copy()
    
    def analyze_requirements(self, requirements: str) -> RequirementAnalysisResult:
        """
        Analyze user requirements and identify needed components.
        
        Args:
            requirements: Natural language description of requirements
            
        Returns:
            RequirementAnalysisResult with identified components
        """
        requirements_lower = requirements.lower()
        needed_types: Set[FlowNodeTypeEnum] = set()
        reasoning = []
        
        # Always add entry point
        needed_types.add(FlowNodeTypeEnum.WORKFLOW_START)
        
        # Match capabilities
        matched_capabilities: List[ComponentCapability] = []
        for capability in self.CAPABILITIES:
            if capability.keyword.lower() in requirements_lower:
                matched_capabilities.append(capability)
        
        # Sort by priority and add node types
        matched_capabilities.sort(key=lambda x: x.priority, reverse=True)
        
        for capability in matched_capabilities:
            for node_type in capability.node_types:
                if node_type not in needed_types:
                    needed_types.add(node_type)
                    reasoning.append(
                        f"Found '{capability.keyword}' in requirements, "
                        f"adding {node_type.value} ({capability.description})"
                    )
        
        # Check for missing components (custom functionality)
        missing = self._detect_missing_components(requirements, needed_types)
        
        # Determine confidence
        if len(matched_capabilities) == 0:
            confidence = 0.5
            reasoning.append("No specific keywords matched, using default simple workflow")
        elif len(missing) > 0:
            confidence = 0.7
            reasoning.append(f"Found {len(missing)} custom requirements needing plugins")
        else:
            confidence = 0.9
            reasoning.append("Successfully identified all required components")
        
        # Add default nodes if needed
        if FlowNodeTypeEnum.CHAT_NODE not in needed_types and FlowNodeTypeEnum.AGENT not in needed_types:
            # Need some AI processing
            pass  # Don't add by default, let caller decide
        
        return RequirementAnalysisResult(
            needed_components=list(needed_types),
            missing_components=missing,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def _detect_missing_components(
        self,
        requirements: str,
        already_covered: Set[FlowNodeTypeEnum]
    ) -> List[MissingComponent]:
        """
        Detect if any requirements need custom plugins.
        
        This is a simplified implementation. In production, this would
        use more sophisticated NLP or a language model.
        """
        missing = []
        requirements_lower = requirements.lower()
        
        # Patterns that suggest custom functionality
        custom_patterns = [
            ("算法", "custom algorithm", ["input_data"], ["result"]),
            ("algorithm", "custom algorithm", ["input_data"], ["result"]),
            ("推荐", "recommendation", ["user_id", "items"], ["recommendations"]),
            ("recommend", "recommendation", ["user_id", "items"], ["recommendations"]),
            ("预测", "prediction", ["data"], ["prediction"]),
            ("predict", "prediction", ["data"], ["prediction"]),
            ("自定义", "custom function", ["input"], ["output"]),
            ("custom", "custom function", ["input"], ["output"]),
        ]
        
        for pattern, name, inputs, outputs in custom_patterns:
            if pattern in requirements_lower:
                # Check if already covered by existing nodes
                covered = False
                for node_type in already_covered:
                    if node_type in [FlowNodeTypeEnum.CODE, FlowNodeTypeEnum.HTTP_REQUEST]:
                        covered = True
                        break
                
                if not covered:
                    missing.append(MissingComponent(
                        required_capability=pattern,
                        suggested_plugin_name=name,
                        suggested_description=f"Custom {name} functionality",
                        required_inputs=[{"name": i, "type": "string"} for i in inputs],
                        required_outputs=[{"name": o, "type": "string"} for o in outputs]
                    ))
        
        return missing
    
    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()


# Singleton instance
_registry: Optional[ComponentRegistry] = None


def get_component_registry(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    team_id: Optional[str] = None
) -> ComponentRegistry:
    """Get or create singleton ComponentRegistry instance"""
    global _registry
    if _registry is None:
        _registry = ComponentRegistry(base_url, api_key, team_id)
    return _registry
