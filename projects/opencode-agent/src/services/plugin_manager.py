"""
PluginManager - Orchestrates plugin generation, creation and workflow integration

This module provides:
1. End-to-end plugin creation workflow
2. Integration of code generation + API creation
3. Workflow building with custom plugins
4. Error handling and validation
"""
from __future__ import annotations
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

from .component_registry import ComponentRegistry, FlowNodeTypeEnum
from .workflow_builder import WorkflowBuilder, SmartWorkflowBuilder, GeneratedWorkflow
from .plugin_code_generator import (
    PluginCodeGenerator,
    PluginSpec,
    PluginInput,
    PluginOutput,
    GeneratedPluginCode,
    PluginLanguage
)
from .fastgpt_plugin_api import (
    FastGPTPluginAPI,
    PluginCreateRequest,
    PluginCreateResponse,
    PluginAPIError
)


@dataclass
class MissingComponent:
    """A component that needs to be created"""
    capability: str
    suggested_name: str
    description: str
    inputs: List[Dict[str, Any]]
    outputs: List[Dict[str, Any]]
    implementation: str


@dataclass
class WorkflowWithPlugins:
    """Workflow that includes custom plugins"""
    workflow: GeneratedWorkflow
    created_plugins: List[PluginCreateResponse]
    missing_components: List[MissingComponent]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class AutomationResult:
    """Result of full automation"""
    success: bool
    workflow: Optional[Dict[str, Any]]
    created_plugins: List[PluginCreateResponse] = field(default_factory=list)
    reasoning: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class PluginManager:
    """
    Manages the complete plugin lifecycle:
    1. Analyze requirements for missing components
    2. Generate plugin code
    3. Create plugin in FastGPT
    4. Build workflow with plugin integration
    """
    
    def __init__(
        self,
        registry: Optional[ComponentRegistry] = None,
        plugin_api: Optional[FastGPTPluginAPI] = None,
        code_generator: Optional[PluginCodeGenerator] = None
    ):
        self.registry = registry or ComponentRegistry()
        self.plugin_api = plugin_api
        self.code_generator = code_generator or PluginCodeGenerator()
        self.workflow_builder = SmartWorkflowBuilder(self.registry)
    
    async def create_plugin_from_requirement(
        self,
        capability: str,
        name: str,
        description: str,
        inputs: List[PluginInput],
        outputs: List[PluginOutput],
        implementation: str,
        language: PluginLanguage = PluginLanguage.TYPESCRIPT
    ) -> PluginCreateResponse:
        """
        Create a plugin from requirement specification.
        
        Steps:
        1. Generate plugin code
        2. Create plugin via API
        3. Return plugin info
        """
        if not self.plugin_api:
            raise ValueError("Plugin API not configured")
        
        # Generate plugin code
        spec = PluginSpec(
            name=name,
            description=description,
            inputs=inputs,
            outputs=outputs,
            implementation=implementation,
            language=language
        )
        
        generated = self.code_generator.generate(spec)
        
        # Create plugin via API
        request = PluginCreateRequest(
            name=name,
            description=description,
            inputs=generated.config["inputs"],
            outputs=generated.config["outputs"],
            code=generated.main_code
        )
        
        response = await self.plugin_api.create_plugin(request)
        
        return response
    
    async def build_workflow_with_custom_plugins(
        self,
        requirements: str,
        auto_create_plugins: bool = True,
        complexity: Optional[str] = None
    ) -> WorkflowWithPlugins:
        """
        Build workflow with automatic plugin creation for missing components.
        
        Args:
            requirements: User requirements in natural language
            auto_create_plugins: Whether to auto-create missing plugins
            complexity: Optional complexity hint
            
        Returns:
            WorkflowWithPlugins containing workflow and created plugins
        """
        # Analyze requirements
        analysis = self.registry.analyze_requirements(requirements)
        
        created_plugins: List[PluginCreateResponse] = []
        missing: List[MissingComponent] = []
        errors: List[str] = []
        warnings: List[str] = []
        
        # Check for missing components
        for mc in analysis.missing_components:
            missing_component = MissingComponent(
                capability=mc.required_capability,
                suggested_name=mc.suggested_plugin_name,
                description=mc.suggested_description,
                inputs=[{"name": i["name"], "type": i["type"]} for i in mc.required_inputs],
                outputs=[{"name": o["name"], "type": o["type"]} for o in mc.required_outputs],
                implementation=f"Implement {mc.suggested_plugin_name} logic"
            )
            missing.append(missing_component)
            
            # Auto-create plugin if enabled
            if auto_create_plugins and self.plugin_api:
                try:
                    plugin_response = await self._create_plugin_for_component(missing_component)
                    created_plugins.append(plugin_response)
                    warnings.append(f"Created plugin: {missing_component.suggested_name}")
                except PluginAPIError as e:
                    errors.append(f"Failed to create plugin {missing_component.suggested_name}: {e}")
        
        # Build workflow
        workflow = self.workflow_builder.build_from_requirements(requirements, complexity)
        
        # Add custom plugin nodes if plugins were created
        if created_plugins:
            workflow = self._integrate_plugins(workflow, created_plugins)
        
        return WorkflowWithPlugins(
            workflow=workflow,
            created_plugins=created_plugins,
            missing_components=missing,
            errors=errors,
            warnings=warnings
        )
    
    async def _create_plugin_for_component(
        self,
        component: MissingComponent
    ) -> PluginCreateResponse:
        """Create a plugin for a missing component"""
        # Convert inputs/outputs to PluginInput/PluginOutput
        inputs = [
            PluginInput(name=i["name"], type=i["type"], required=True)
            for i in component.inputs
        ]
        outputs = [
            PluginOutput(name=o["name"], type=o["type"])
            for o in component.outputs
        ]
        
        return await self.create_plugin_from_requirement(
            capability=component.capability,
            name=component.suggested_name,
            description=component.description,
            inputs=inputs,
            outputs=outputs,
            implementation=component.implementation
        )
    
    def _integrate_plugins(
        self,
        workflow: GeneratedWorkflow,
        plugins: List[PluginCreateResponse]
    ) -> GeneratedWorkflow:
        """Integrate created plugins into the workflow"""
        # Add plugin nodes to the workflow
        # This is a simplified version - in production, you'd add proper node types
        for plugin in plugins:
            # Add plugin module node
            node_id = self.workflow_builder.add_node(
                FlowNodeTypeEnum.PLUGIN_MODULE,
                name=plugin.name,
                config={"pluginId": plugin.plugin_id}
            )
        
        # Re-validate
        validation = self.workflow_builder.validate()
        
        return GeneratedWorkflow(
            nodes=self.workflow_builder._nodes,
            edges=self.workflow_builder._edges,
            validation=validation,
            metadata={
                **workflow.metadata,
                "plugins_integrated": len(plugins),
                "plugin_ids": [p.plugin_id for p in plugins]
            }
        )
    
    async def automate(
        self,
        requirements: str,
        auto_create_plugins: bool = True,
        complexity: Optional[str] = None
    ) -> AutomationResult:
        """
        Full automation: analyze -> generate code -> create plugins -> build workflow
        
        This is the main entry point for the complete workflow.
        """
        reasoning = []
        errors = []
        warnings = []
        
        try:
            # Step 1: Analyze requirements
            reasoning.append(f"Analyzing requirements: {requirements}")
            analysis = self.registry.analyze_requirements(requirements)
            reasoning.append(f"Identified {len(analysis.needed_components)} components")
            
            if analysis.missing_components:
                reasoning.append(f"Found {len(analysis.missing_components)} components needing custom plugins")
            
            # Step 2: Build workflow
            reasoning.append("Building workflow structure...")
            result = await self.build_workflow_with_custom_plugins(
                requirements=requirements,
                auto_create_plugins=auto_create_plugins,
                complexity=complexity
            )
            
            reasoning.extend([f"Created plugin: {p.name}" for p in result.created_plugins])
            errors.extend(result.errors)
            warnings.extend(result.warnings)
            
            # Step 3: Export workflow
            workflow_json = result.workflow.to_fastgpt_format()
            
            return AutomationResult(
                success=len(errors) == 0,
                workflow=workflow_json,
                created_plugins=result.created_plugins,
                reasoning=reasoning,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            reasoning.append(f"Error: {str(e)}")
            errors.append(str(e))
            
            return AutomationResult(
                success=False,
                workflow=None,
                reasoning=reasoning,
                errors=errors
            )


# Factory function
def create_plugin_manager(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    team_id: Optional[str] = None
) -> PluginManager:
    """Create a PluginManager with optional API configuration"""
    plugin_api = None
    if api_key or team_id:
        plugin_api = FastGPTPluginAPI(base_url, api_key, team_id)
    
    return PluginManager(plugin_api=plugin_api)
