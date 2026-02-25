"""
Validation Engine - Layered validation (Static + Sandbox)
"""

import os
import json
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel
import httpx


class ValidationLevel(str, Enum):
    """Validation levels"""

    STATIC = "static"  # JSON syntax, schema, type compatibility
    SANDBOX = "sandbox"  # Mock runtime testing
    SECURITY = "security"  # Security lint


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues"""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    """A single validation issue"""

    level: ValidationLevel
    severity: ValidationSeverity
    message: str
    node_id: Optional[str] = None
    edge_id: Optional[str] = None
    suggestion: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of validation"""

    is_valid: bool
    issues: List[ValidationIssue]
    passed_levels: List[ValidationLevel]

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]


class StaticValidator:
    """First layer: Static type checking"""

    REQUIRED_NODE_FIELDS = ["nodeId", "flowNodeType", "name"]
    REQUIRED_EDGE_FIELDS = ["source", "target"]

    # Node type compatibility matrix
    NODE_OUTPUT_TYPES = {
        "workflowStart": {"userChatInput": "string"},
        "chatNode": {"responseText": "string", "history": "array"},
        "datasetSearchNode": {"quoteList": "array"},
        "datasetConcatNode": {"quoteList": "array"},
        "answerNode": {"answerText": "string"},
        "ifElseNode": {"true": "string", "false": "string"},
        "httpRequest468": {"response": "object"},
        "code": {"output": "string"},
        "classifyQuestion": {"selectedClassIndex": "number"},
        "contentExtract": {"extractedFields": "object"},
        "agent": {"responseText": "string"},
    }

    def validate(self, nodes: List[Dict], edges: List[Dict]) -> List[ValidationIssue]:
        """Run static validation"""
        issues = []

        # 1. Check JSON syntax (already parsed, so skip)

        # 2. Check required fields
        for i, node in enumerate(nodes):
            for field in self.REQUIRED_NODE_FIELDS:
                if field not in node:
                    issues.append(
                        ValidationIssue(
                            level=ValidationLevel.STATIC,
                            severity=ValidationSeverity.ERROR,
                            message=f"Node {i} missing required field: {field}",
                            node_id=node.get("nodeId"),
                            suggestion=f"Add '{field}' field to node",
                        )
                    )

        for i, edge in enumerate(edges):
            for field in self.REQUIRED_EDGE_FIELDS:
                if field not in edge:
                    issues.append(
                        ValidationIssue(
                            level=ValidationLevel.STATIC,
                            severity=ValidationSeverity.ERROR,
                            message=f"Edge {i} missing required field: {field}",
                            edge_id=f"edge_{i}",
                            suggestion=f"Add '{field}' field to edge",
                        )
                    )

        # 3. Check node types exist
        valid_node_types = set(self.NODE_OUTPUT_TYPES.keys())
        for node in nodes:
            node_type = node.get("flowNodeType")
            if node_type and node_type not in valid_node_types:
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.STATIC,
                        severity=ValidationSeverity.WARNING,
                        message=f"Unknown node type: {node_type}",
                        node_id=node.get("nodeId"),
                        suggestion="Check if this is a custom node type",
                    )
                )

        # 4. Check workflowStart exists
        node_types = [n.get("flowNodeType") for n in nodes]
        if "workflowStart" not in node_types:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.STATIC,
                    severity=ValidationSeverity.ERROR,
                    message="Workflow must have a workflowStart node",
                    suggestion="Add a workflowStart node as the entry point",
                )
            )

        # 5. Check answerNode or terminal node exists
        if not any(nt in node_types for nt in ["answerNode", "pluginOutput"]):
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.STATIC,
                    severity=ValidationSeverity.WARNING,
                    message="Workflow should have an output node (answerNode or similar)",
                    suggestion="Add an answerNode as the final output",
                )
            )

        # 6. Check edge references are valid
        node_ids = set(n.get("nodeId") for n in nodes)
        for edge in edges:
            if edge.get("source") not in node_ids:
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.STATIC,
                        severity=ValidationSeverity.ERROR,
                        message=f"Edge references non-existent source node: {edge.get('source')}",
                        edge_id=f"edge_{edge.get('source')}_{edge.get('target')}",
                        suggestion="Use a valid node ID as source",
                    )
                )
            if edge.get("target") not in node_ids:
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.STATIC,
                        severity=ValidationSeverity.ERROR,
                        message=f"Edge references non-existent target node: {edge.get('target')}",
                        edge_id=f"edge_{edge.get('source')}_{edge.get('target')}",
                        suggestion="Use a valid node ID as target",
                    )
                )

        # 7. Check for orphan nodes
        connected_nodes = set()
        for edge in edges:
            connected_nodes.add(edge.get("source"))
            connected_nodes.add(edge.get("target"))

        orphan_nodes = node_ids - connected_nodes
        if orphan_nodes and len(nodes) > 1:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.STATIC,
                    severity=ValidationSeverity.WARNING,
                    message=f"Orphan nodes detected (not connected): {orphan_nodes}",
                    suggestion="Connect all nodes or remove orphan nodes",
                )
            )

        # 8. Type compatibility check (basic)
        # This is handled more thoroughly by VariableMappingEngine

        return issues


class SecurityValidator:
    """Third layer: Security lint checking"""

    DANGEROUS_PATTERNS = [
        "eval(",
        "exec(",
        "import os",
        "import socket",
        "__import__",
        "subprocess",
        "spawn(",
    ]

    def validate(self, nodes: List[Dict], edges: List[Dict]) -> List[ValidationIssue]:
        """Run security validation"""
        issues = []

        for node in nodes:
            node_type = node.get("flowNodeType")

            # Check code nodes for dangerous patterns
            if node_type == "code":
                code = ""
                # Try to find code in inputs
                inputs = node.get("inputs", [])
                for inp in inputs:
                    if inp.get("key") == "code":
                        code = inp.get("value", "")
                        break

                if code:
                    for pattern in self.DANGEROUS_PATTERNS:
                        if pattern in code:
                            issues.append(
                                ValidationIssue(
                                    level=ValidationLevel.SECURITY,
                                    severity=ValidationSeverity.ERROR,
                                    message=f"Security: Dangerous pattern '{pattern}' found in code node",
                                    node_id=node.get("nodeId"),
                                    suggestion="Remove dangerous patterns for security",
                                )
                            )

            # Check HTTP nodes for sensitive data
            if node_type == "httpRequest468":
                url = ""
                inputs = node.get("inputs", [])
                for inp in inputs:
                    if inp.get("key") == "url":
                        url = inp.get("value", "")
                        break

                if url:
                    # Check for potential secrets in URL
                    sensitive_patterns = ["api_key", "password", "secret", "token"]
                    for pattern in sensitive_patterns:
                        if pattern in url.lower():
                            issues.append(
                                ValidationIssue(
                                    level=ValidationLevel.SECURITY,
                                    severity=ValidationSeverity.WARNING,
                                    message=f"Potential sensitive data in HTTP URL",
                                    node_id=node.get("nodeId"),
                                    suggestion="Use environment variables for sensitive data",
                                )
                            )

        return issues


class SandboxValidator:
    """Second layer: Sandbox runtime testing"""

    def __init__(self, sandbox_url: Optional[str] = None):
        self.sandbox_url = sandbox_url or os.environ.get(
            "SANDBOX_URL", "http://localhost:3001"
        )
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def validate(
        self, nodes: List[Dict], edges: List[Dict], mock_data: Optional[Dict] = None
    ) -> List[ValidationIssue]:
        """Run sandbox validation with mock data"""
        issues = []

        # Prepare mock data for testing
        if mock_data is None:
            mock_data = self._generate_mock_data(nodes)

        try:
            # Call sandbox API to validate workflow
            response = await self.client.post(
                f"{self.sandbox_url}/api/validate",
                json={
                    "nodes": nodes,
                    "edges": edges,
                    "mock_data": mock_data,
                    "mode": "test",
                },
            )

            if response.status_code == 200:
                result = response.json()
                if not result.get("success"):
                    for error in result.get("errors", []):
                        issues.append(
                            ValidationIssue(
                                level=ValidationLevel.SANDBOX,
                                severity=ValidationSeverity.ERROR,
                                message=error.get(
                                    "message", "Sandbox validation failed"
                                ),
                                node_id=error.get("node_id"),
                                suggestion=error.get("suggestion"),
                            )
                        )
            else:
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.SANDBOX,
                        severity=ValidationSeverity.WARNING,
                        message=f"Sandbox validation returned status {response.status_code}",
                        suggestion="Check sandbox service is running",
                    )
                )

        except Exception as e:
            # Sandbox not available - skip this level
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.SANDBOX,
                    severity=ValidationSeverity.INFO,
                    message=f"Sandbox validation skipped: {str(e)}",
                    suggestion="Ensure sandbox service is running",
                )
            )

        return issues

    def _generate_mock_data(self, nodes: List[Dict]) -> Dict:
        """Generate mock data for workflow testing"""
        mock_data = {}

        for node in nodes:
            node_type = node.get("flowNodeType")
            node_id = node.get("nodeId")

            if node_type == "workflowStart":
                mock_data[node_id] = {"userChatInput": "test query"}
            elif node_type == "chatNode":
                mock_data[node_id] = {
                    "responseText": "This is a mock AI response",
                    "history": [],
                }
            elif node_type == "datasetSearchNode":
                mock_data[node_id] = {
                    "quoteList": [
                        {"content": "Mock document 1", "score": 0.9},
                        {"content": "Mock document 2", "score": 0.8},
                    ]
                }
            elif node_type == "httpRequest468":
                mock_data[node_id] = {
                    "response": {"status": 200, "data": "mock response"}
                }
            elif node_type == "code":
                mock_data[node_id] = {"output": "mock code output"}

        return mock_data


class ValidationEngine:
    """Main validation engine with layered validation"""

    def __init__(self, sandbox_url: Optional[str] = None, enable_sandbox: bool = True):
        self.static_validator = StaticValidator()
        self.security_validator = SecurityValidator()
        self.sandbox_validator = (
            SandboxValidator(sandbox_url) if enable_sandbox else None
        )
        self.enable_sandbox = enable_sandbox

    async def close(self):
        if self.sandbox_validator:
            await self.sandbox_validator.close()

    async def validate(
        self,
        nodes: List[Dict],
        edges: List[Dict],
        levels: Optional[List[ValidationLevel]] = None,
        mock_data: Optional[Dict] = None,
    ) -> ValidationResult:
        """
        Run layered validation on workflow

        Args:
            nodes: Workflow nodes
            edges: Workflow edges
            levels: Which validation levels to run (default: all)
            mock_data: Optional mock data for sandbox testing

        Returns:
            ValidationResult with all issues
        """
        if levels is None:
            levels = [ValidationLevel.STATIC, ValidationLevel.SECURITY]
            if self.enable_sandbox:
                levels.append(ValidationLevel.SANDBOX)

        all_issues = []
        passed_levels = []

        # Layer 1: Static validation (always run)
        if ValidationLevel.STATIC in levels:
            static_issues = self.static_validator.validate(nodes, edges)
            all_issues.extend(static_issues)
            if not any(i.severity == ValidationSeverity.ERROR for i in static_issues):
                passed_levels.append(ValidationLevel.STATIC)

        # Layer 2: Security validation (always run)
        if ValidationLevel.SECURITY in levels:
            security_issues = self.security_validator.validate(nodes, edges)
            all_issues.extend(security_issues)
            if not any(i.severity == ValidationSeverity.ERROR for i in security_issues):
                passed_levels.append(ValidationLevel.SECURITY)

        # Layer 3: Sandbox validation (optional)
        if ValidationLevel.SANDBOX in levels and self.sandbox_validator:
            sandbox_issues = await self.sandbox_validator.validate(
                nodes, edges, mock_data
            )
            all_issues.extend(sandbox_issues)
            if not any(i.severity == ValidationSeverity.ERROR for i in sandbox_issues):
                passed_levels.append(ValidationLevel.SANDBOX)

        # Determine overall validity
        has_errors = any(i.severity == ValidationSeverity.ERROR for i in all_issues)

        return ValidationResult(
            is_valid=not has_errors, issues=all_issues, passed_levels=passed_levels
        )

    async def validate_only_static(
        self, nodes: List[Dict], edges: List[Dict]
    ) -> ValidationResult:
        """Run only static validation"""
        return await self.validate(nodes, edges, levels=[ValidationLevel.STATIC])

    async def validate_full(
        self, nodes: List[Dict], edges: List[Dict], mock_data: Optional[Dict] = None
    ) -> ValidationResult:
        """Run full validation including sandbox"""
        return await self.validate(nodes, edges, mock_data=mock_data)
