"""
Services package for OpenCode-Agent

Core services for FastGPT workflow automation:
- ComponentRegistry: Discovers FastGPT nodes and plugins
- WorkflowBuilder: Builds FastGPT workflows
- PluginCodeGenerator: Generates plugin code
- FastGPTPluginAPI: Manages plugins via API
- PluginManager: Orchestrates everything
"""
from .component_registry import (
    ComponentRegistry,
    FlowNodeTypeEnum,
    NodeCategory,
    get_component_registry
)

from .workflow_builder import (
    WorkflowBuilder,
    SmartWorkflowBuilder,
    LayoutAlgorithm,
    GeneratedWorkflow,
    WorkflowValidationResult
)

from .plugin_code_generator import (
    PluginCodeGenerator,
    PluginSpec,
    PluginInput,
    PluginOutput,
    GeneratedPluginCode,
    PluginLanguage,
    create_plugin_generator
)

from .fastgpt_plugin_api import (
    FastGPTPluginAPI,
    PluginCreateRequest,
    PluginCreateResponse,
    PluginAPIError,
    create_plugin_api
)

from .plugin_manager import (
    PluginManager,
    create_plugin_manager,
    AutomationResult,
    WorkflowWithPlugins
)

__all__ = [
    # Component Registry
    "ComponentRegistry",
    "FlowNodeTypeEnum",
    "NodeCategory",
    "get_component_registry",
    
    # Workflow Builder
    "WorkflowBuilder",
    "SmartWorkflowBuilder",
    "LayoutAlgorithm",
    "GeneratedWorkflow",
    "WorkflowValidationResult",
    
    # Plugin Code Generator
    "PluginCodeGenerator",
    "PluginSpec",
    "PluginInput",
    "PluginOutput",
    "GeneratedPluginCode",
    "PluginLanguage",
    "create_plugin_generator",
    
    # FastGPT Plugin API
    "FastGPTPluginAPI",
    "PluginCreateRequest",
    "PluginCreateResponse",
    "PluginAPIError",
    "create_plugin_api",
    
    # Plugin Manager
    "PluginManager",
    "create_plugin_manager",
    "AutomationResult",
    "WorkflowWithPlugins",
]
