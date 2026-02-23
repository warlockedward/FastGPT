"""
Tests for IntentAnalyzer - RED phase (tests should fail first)
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestIntentAnalyzer:
    """Test suite for IntentAnalyzer class"""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for testing"""
        client = AsyncMock()
        client.chat = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_analyze_create_workflow_intent(self):
        """Verify it detects 'create a chatbot' as create_workflow intent"""
        from src.agent.intent_analyzer import IntentAnalyzer
        
        # This should fail because IntentAnalyzer doesn't exist yet
        analyzer = IntentAnalyzer(base_url="http://localhost:3000", api_key="test-key")
        result = await analyzer.analyze("create a chatbot for customer support")
        
        assert result.intent == "create_workflow"
        assert result.complexity in ["simple", "medium", "complex"]
    
    @pytest.mark.asyncio
    async def test_extract_workflow_requirements(self):
        """Verify it extracts requirements from natural language"""
        from src.agent.intent_analyzer import IntentAnalyzer
        
        analyzer = IntentAnalyzer(base_url="http://localhost:3000", api_key="test-key")
        result = await analyzer.analyze(
            "I need a workflow that searches a knowledge base about pricing "
            "and then responds with the prices"
        )
        
        assert result.requirements is not None
        assert "knowledge" in result.requirements.lower() or "pricing" in result.requirements.lower()
    
    @pytest.mark.asyncio
    async def test_analyze_complexity_simple(self):
        """Verify it estimates simple workflow complexity"""
        from src.agent.intent_analyzer import IntentAnalyzer
        
        analyzer = IntentAnalyzer(base_url="http://localhost:3000", api_key="test-key")
        result = await analyzer.analyze("create a simple chatbot")
        
        assert result.complexity == "simple"
    
    @pytest.mark.asyncio
    async def test_analyze_complexity_complex(self):
        """Verify it estimates complex workflow complexity"""
        from src.agent.intent_analyzer import IntentAnalyzer
        
        analyzer = IntentAnalyzer(base_url="http://localhost:3000", api_key="test-key")
        result = await analyzer.analyze(
            "create a workflow that checks user authentication, "
            "searches multiple knowledge bases, runs custom code, "
            "sends notifications, and handles errors with retries"
        )
        
        assert result.complexity == "complex"
    
    @pytest.mark.asyncio
    async def test_analyze_modify_workflow_intent(self):
        """Verify it detects modify workflow intent"""
        from src.agent.intent_analyzer import IntentAnalyzer
        
        analyzer = IntentAnalyzer(base_url="http://localhost:3000", api_key="test-key")
        result = await analyzer.analyze("add a knowledge base search to my existing workflow")
        
        assert result.intent == "modify_workflow"
    
    @pytest.mark.asyncio
    async def test_analyze_ask_question_intent(self):
        """Verify it detects ask question intent"""
        from src.agent.intent_analyzer import IntentAnalyzer
        
        analyzer = IntentAnalyzer(base_url="http://localhost:3000", api_key="test-key")
        result = await analyzer.analyze("how do I create a workflow?")
        
        assert result.intent == "ask_question"
