"""
FastGPT Plugin API Client

This module provides:
1. Plugin CRUD operations via FastGPT API
2. Plugin installation/uninstallation
3. Plugin template management
4. Tool registration
"""
from __future__ import annotations
import os
import json
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum

import httpx


class PluginStatus(str, Enum):
    """Plugin status"""
    DRAFT = "draft"
    PUBLISHED = "published"
    INSTALLED = "installed"
    DISABLED = "disabled"


@dataclass
class PluginInfo:
    """Plugin information from API"""
    id: str
    name: str
    description: str
    version: str
    status: PluginStatus
    team_id: str
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass
class PluginCreateRequest:
    """Request to create a plugin"""
    name: str
    description: str
    version: str = "1.0.0"
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    code: Optional[str] = None


@dataclass
class PluginCreateResponse:
    """Response from plugin creation"""
    plugin_id: str
    name: str
    status: PluginStatus
    api_endpoint: str


@dataclass
class ToolInfo:
    """Tool information"""
    id: str
    name: str
    description: str
    type: str
    parameters: Dict[str, Any] = field(default_factory=dict)


class FastGPTPluginAPI:
    """
    FastGPT Plugin API Client
    
    Provides methods to:
    - Create, read, update, delete plugins
    - Install/uninstall plugins to teams
    - Manage plugin templates
    - Register tools
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        team_id: Optional[str] = None
    ):
        self.base_url = base_url or os.environ.get("FASTGPT_API_URL", "http://fastgpt:3000")
        self.api_key = api_key or os.environ.get("FASTGPT_API_KEY", "")
        self.team_id = team_id or os.environ.get("FASTGPT_TEAM_ID", "")
        
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    # ==================== Plugin CRUD ====================
    
    async def create_plugin(self, request: PluginCreateRequest) -> PluginCreateResponse:
        """
        Create a new plugin.
        
        POST /api/v1/team/plugin/create
        """
        response = await self.client.post(
            f"{self.base_url}/api/v1/team/plugin/create",
            json={
                "teamId": self.team_id,
                "name": request.name,
                "description": request.description,
                "version": request.version,
                "inputs": request.inputs,
                "outputs": request.outputs,
                "tags": request.tags,
                "code": request.code,
            }
        )
        
        if response.status_code != 200:
            raise PluginAPIError(
                f"Failed to create plugin: {response.status_code}",
                status_code=response.status_code,
                response=response.text
            )
        
        data = response.json()
        return PluginCreateResponse(
            plugin_id=data.get("id", data.get("pluginId", "")),
            name=data.get("name", request.name),
            status=PluginStatus(data.get("status", "draft")),
            api_endpoint=f"/api/v1/team/plugin/{data.get('id') or data.get('pluginId')}/execute"
        )
    
    async def get_plugin(self, plugin_id: str) -> PluginInfo:
        """
        Get plugin details.
        
        GET /api/v1/team/plugin/:id
        """
        response = await self.client.get(
            f"{self.base_url}/api/v1/team/plugin/{plugin_id}",
            params={"teamId": self.team_id}
        )
        
        if response.status_code != 200:
            raise PluginAPIError(
                f"Failed to get plugin: {response.status_code}",
                status_code=response.status_code,
                response=response.text
            )
        
        data = response.json()
        return PluginInfo(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            status=PluginStatus(data.get("status", "draft")),
            team_id=data.get("teamId", self.team_id),
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", []),
            created_at=data.get("createdAt", ""),
            updated_at=data.get("updatedAt", "")
        )
    
    async def list_plugins(self, status: Optional[PluginStatus] = None) -> List[PluginInfo]:
        """
        List all plugins in the team.
        
        POST /api/v1/team/plugin/list
        """
        json_data: Dict[str, Any] = {"teamId": self.team_id}
        if status:
            json_data["status"] = status.value
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/team/plugin/list",
            json=json_data
        )
        
        if response.status_code != 200:
            raise PluginAPIError(
                f"Failed to list plugins: {response.status_code}",
                status_code=response.status_code,
                response=response.text
            )
        
        data = response.json()
        plugins = []
        for item in data.get("data", []):
            plugins.append(PluginInfo(
                id=item.get("id", ""),
                name=item.get("name", ""),
                description=item.get("description", ""),
                version=item.get("version", "1.0.0"),
                status=PluginStatus(item.get("status", "draft")),
                team_id=item.get("teamId", self.team_id),
                inputs=item.get("inputs", []),
                outputs=item.get("outputs", []),
                created_at=item.get("createdAt", ""),
                updated_at=item.get("updatedAt", "")
            ))
        
        return plugins
    
    async def update_plugin(
        self,
        plugin_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        inputs: Optional[List[Dict[str, Any]]] = None,
        outputs: Optional[List[Dict[str, Any]]] = None,
        code: Optional[str] = None
    ) -> PluginInfo:
        """
        Update plugin.
        
        PUT /api/v1/team/plugin/:id
        """
        update_data: Dict[str, Any] = {"teamId": self.team_id}
        
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if inputs is not None:
            update_data["inputs"] = inputs
        if outputs is not None:
            update_data["outputs"] = outputs
        if code is not None:
            update_data["code"] = code
        
        response = await self.client.put(
            f"{self.base_url}/api/v1/team/plugin/{plugin_id}",
            json=update_data
        )
        
        if response.status_code != 200:
            raise PluginAPIError(
                f"Failed to update plugin: {response.status_code}",
                status_code=response.status_code,
                response=response.text
            )
        
        return await self.get_plugin(plugin_id)
    
    async def delete_plugin(self, plugin_id: str) -> bool:
        """
        Delete a plugin.
        
        DELETE /api/v1/team/plugin/:id
        """
        response = await self.client.delete(
            f"{self.base_url}/api/v1/team/plugin/{plugin_id}",
            params={"teamId": self.team_id}
        )
        
        if response.status_code not in [200, 204]:
            raise PluginAPIError(
                f"Failed to delete plugin: {response.status_code}",
                status_code=response.status_code,
                response=response.text
            )
        
        return True
    
    # ==================== Plugin Installation ====================
    
    async def install_plugin(self, plugin_id: str) -> bool:
        """
        Install plugin to current team.
        
        POST /api/v1/team/plugin/:id/install
        """
        response = await self.client.post(
            f"{self.base_url}/api/v1/team/plugin/{plugin_id}/install",
            json={"teamId": self.team_id}
        )
        
        if response.status_code != 200:
            raise PluginAPIError(
                f"Failed to install plugin: {response.status_code}",
                status_code=response.status_code,
                response=response.text
            )
        
        return True
    
    async def uninstall_plugin(self, plugin_id: str) -> bool:
        """
        Uninstall plugin from current team.
        
        POST /api/v1/team/plugin/:id/uninstall
        """
        response = await self.client.post(
            f"{self.base_url}/api/v1/team/plugin/{plugin_id}/uninstall",
            json={"teamId": self.team_id}
        )
        
        if response.status_code != 200:
            raise PluginAPIError(
                f"Failed to uninstall plugin: {response.status_code}",
                status_code=response.status_code,
                response=response.text
            )
        
        return True
    
    # ==================== Tools ====================
    
    async def list_tools(self) -> List[ToolInfo]:
        """
        List available tools.
        
        POST /api/core/app/tool/getSystemToolTemplates
        """
        response = await self.client.post(
            f"{self.base_url}/api/core/app/tool/getSystemToolTemplates",
            json={"teamId": self.team_id}
        )
        
        if response.status_code != 200:
            raise PluginAPIError(
                f"Failed to list tools: {response.status_code}",
                status_code=response.status_code,
                response=response.text
            )
        
        data = response.json()
        tools = []
        for item in data.get("data", []):
            tools.append(ToolInfo(
                id=item.get("id", ""),
                name=item.get("name", ""),
                description=item.get("description", ""),
                type=item.get("type", "http"),
                parameters=item.get("parameters", {})
            ))
        
        return tools
    
    async def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler_code: str
    ) -> ToolInfo:
        """
        Register a custom tool.
        
        POST /api/core/app/tool/register
        """
        response = await self.client.post(
            f"{self.base_url}/api/core/app/tool/register",
            json={
                "teamId": self.team_id,
                "name": name,
                "description": description,
                "parameters": parameters,
                "handlerCode": handler_code
            }
        )
        
        if response.status_code != 200:
            raise PluginAPIError(
                f"Failed to register tool: {response.status_code}",
                status_code=response.status_code,
                response=response.text
            )
        
        data = response.json()
        return ToolInfo(
            id=data.get("id", ""),
            name=data.get("name", name),
            description=data.get("description", description),
            type="custom",
            parameters=parameters
        )
    
    # ==================== Utility ====================
    
    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()
    
    async def health_check(self) -> bool:
        """Check if API is accessible"""
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/health")
            return response.status_code == 200
        except Exception:
            return False


class PluginAPIError(Exception):
    """Plugin API Error"""
    
    def __init__(
        self,
        message: str,
        status_code: int = 0,
        response: str = ""
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


# Factory function
def create_plugin_api(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    team_id: Optional[str] = None
) -> FastGPTPluginAPI:
    """Create FastGPT Plugin API client"""
    return FastGPTPluginAPI(base_url, api_key, team_id)
