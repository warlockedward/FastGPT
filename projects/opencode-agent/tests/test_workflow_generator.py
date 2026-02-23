"""
Tests for WorkflowGenerator - RED phase (tests should fail first)
"""
import pytest
from unittest.mock import AsyncMock


class TestWorkflowGenerator:
    """Test suite for WorkflowGenerator class"""
    
    @pytest.mark.asyncio
    async def test_generate_simple_chat_workflow(self):
        """Verify it generates workflowStart -> chatNode -> answerNode"""
        from src.agent.workflow_generator import WorkflowGenerator, WorkflowResult
        
        generator = WorkflowGenerator(base_url="http://localhost:3000", api_key="test-key")
        result = await generator.generate(
            intent="create_workflow",
            complexity="simple",
            requirements="Create a simple chatbot that responds to user messages"
        )
        
        assert isinstance(result, WorkflowResult)
        assert len(result.nodes) >= 3
        assert len(result.edges) >= 2
        
        # Check node types exist
        node_types = [n.flowNodeType for n in result.nodes]
        assert "workflowStart" in node_types
        assert "chatNode" in node_types
        assert "answerNode" in node_types
        
        # Check edges connect properly
        source_nodes = [e.source for e in result.edges]
        target_nodes = [e.target for e in result.edges]
        assert len(source_nodes) == len(set(source_nodes))  # Each source used once
    
    @pytest.mark.asyncio
    async def test_generate_rag_workflow(self):
        """Verify it generates RAG workflow with knowledge base"""
        from src.agent.workflow_generator import WorkflowGenerator
        
        generator = WorkflowGenerator(base_url="http://localhost:3000", api_key="test-key")
        result = await generator.generate(
            intent="create_workflow",
            complexity="medium",
            requirements="Create a chatbot that searches a knowledge base and responds"
        )
        
        node_types = [n.flowNodeType for n in result.nodes]
        
        # Should have knowledge base search
        assert "workflowStart" in node_types
        assert "datasetSearchNode" in node_types
        assert "chatNode" in node_types
        assert "answerNode" in node_types
    
    @pytest.mark.asyncio
    async def test_validate_workflow_valid(self):
        """Verify validation passes for valid workflow"""
        from src.agent.workflow_generator import WorkflowGenerator, ValidationResult
        
        generator = WorkflowGenerator()
        
        # Valid workflow: workflowStart -> chatNode -> answerNode
        nodes = [
            {"nodeId": "start", "flowNodeType": "workflowStart", "name": "Start"},
            {"nodeId": "chat", "flowNodeType": "chatNode", "name": "Chat"},
            {"nodeId": "answer", "flowNodeType": "answerNode", "name": "Answer"}
        ]
        edges = [
            {"source": "start", "sourceHandle": "out", "target": "chat", "targetHandle": "in"},
            {"source": "chat", "sourceHandle": "out", "target": "answer", "targetHandle": "in"}
        ]
        
        result = await generator.validate(nodes, edges)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_validate_workflow_missing_start(self):
        """Verify validation fails when workflowStart is missing"""
        from src.agent.workflow_generator import WorkflowGenerator
        
        generator = WorkflowGenerator()
        
        nodes = [
            {"nodeId": "chat", "flowNodeType": "chatNode", "name": "Chat"},
            {"nodeId": "answer", "flowNodeType": "answerNode", "name": "Answer"}
        ]
        edges = [
            {"source": "chat", "sourceHandle": "out", "target": "answer", "targetHandle": "in"}
        ]
        
        result = await generator.validate(nodes, edges)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_generate_complex_workflow(self):
        """Verify it generates complex workflow with conditionals"""
        from src.agent.workflow_generator import WorkflowGenerator
        
        generator = WorkflowGenerator(base_url="http://localhost:3000", api_key="test-key")
        result = await generator.generate(
            intent="create_workflow",
            complexity="complex",
            requirements="Create a workflow that checks user authentication, searches knowledge base, "
                       "runs custom code for processing, sends notifications on completion"
        )
        
        node_types = [n.flowNodeType for n in result.nodes]
        
        # Complex should have more nodes
        assert len(result.nodes) >= 5
        
        # Should have various node types
        assert "workflowStart" in node_types
        assert "datasetSearchNode" in node_types or "chatNode" in node_types
    
    @pytest.mark.asyncio
    async def test_node_positions_readable(self):
        """Verify nodes are positioned in readable layout"""
        from src.agent.workflow_generator import WorkflowGenerator
        
        generator = WorkflowGenerator(base_url="http://localhost:3000", api_key="test-key")
        result = await generator.generate(
            intent="create_workflow",
            complexity="simple",
            requirements="Create a simple chatbot"
        )
        
        # Nodes should have valid positions
        for node in result.nodes:
            assert node.position is not None
            assert node.position.x >= 0
            assert node.position.y >= 0
        
        # Verify vertical flow (y increases)
        start_node = next((n for n in result.nodes if n.flowNodeType == "workflowStart"), None)
        if start_node:
            answer_node = next((n for n in result.nodes if n.flowNodeType == "answerNode"), None)
            if answer_node:
                assert answer_node.position.y > start_node.position.y
