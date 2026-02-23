"""
IntentAnalyzer - Analyzes user messages to determine intent and extract workflow requirements
"""
import json
import os
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import httpx


class IntentType(str, Enum):
    """Intent types for workflow generation"""
    CREATE_WORKFLOW = "create_workflow"
    MODIFY_WORKFLOW = "modify_workflow"
    ASK_QUESTION = "ask_question"
    CLARIFY = "clarify"
    UNKNOWN = "unknown"


class ComplexityType(str, Enum):
    """Workflow complexity levels"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class IntentResult(BaseModel):
    """Result of intent analysis"""
    intent: IntentType
    complexity: ComplexityType
    requirements: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class IntentAnalyzer:
    """Analyzes user messages to determine intent and extract workflow requirements"""
    
    SYSTEM_PROMPT = """You are an AI Workflow intent analyzer. Your task is to analyze user messages
and determine what they want to do with workflow creation.

Analyze the message and respond with a JSON object containing:
- intent: One of "create_workflow", "modify_workflow", "ask_question", "clarify", or "unknown"
- complexity: One of "simple", "medium", or "complex" (based on number of features/nodes needed)
- requirements: A brief description of what the user wants

Intent classification rules:
- "create_workflow": User wants to create a new workflow
- "modify_workflow": User wants to modify, update, or extend an existing workflow
- "ask_question": User is asking how to do something, not requesting a workflow
- "clarify": User is asking clarifying questions about an existing workflow
- "unknown": Cannot determine intent

Complexity guidelines:
- "simple": 1-2 nodes (e.g., simple chatbot, single knowledge base search)
- "medium": 3-4 nodes (e.g., knowledge base search + chat + conditional logic)
- "complex": 5+ nodes (e.g., authentication + multiple knowledge bases + custom code + notifications + error handling)

Respond ONLY with valid JSON, no other text."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or os.environ.get("FASTGPT_API_URL", "http://fastgpt:3000")
        self.api_key = api_key or os.environ.get("FASTGPT_API_KEY", "")
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def analyze(self, message: str) -> IntentResult:
        """
        Analyze a user message to determine intent and extract requirements.
        
        Args:
            message: The user's message
            
        Returns:
            IntentResult with intent, complexity, and requirements
        """
        # Try to use LLM for analysis
        try:
            return await self._analyze_with_llm(message)
        except Exception as e:
            # Fallback to rule-based analysis if LLM fails
            return self._rule_based_analysis(message)
    
    async def _analyze_with_llm(self, message: str) -> IntentResult:
        """Use LLM to analyze the message"""
        # Call FastGPT API
        url = f"{self.base_url}/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": message}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }
        
        response = await self.client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Parse JSON from response
        try:
            # Try to find JSON in the response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                result = json.loads(json_str)
                
                return IntentResult(
                    intent=IntentType(result.get("intent", "unknown")),
                    complexity=ComplexityType(result.get("complexity", "simple")),
                    requirements=result.get("requirements"),
                    confidence=0.8
                )
        except (json.JSONDecodeError, KeyError):
            pass
        
        # If JSON parsing fails, use fallback
        return self._rule_based_analysis(message)
    
    def _rule_based_analysis(self, message: str) -> IntentResult:
        """Fallback rule-based analysis"""
        message_lower = message.lower()
        
        # Determine intent - check ask_question FIRST since it's more specific
        intent = IntentType.UNKNOWN
        
        # Ask question patterns (check first - most specific)
        ask_patterns = [
            "how do i", "how to", "what is", "can you explain",
            "what's", "how does", "?", "what are"
        ]
        
        for pattern in ask_patterns:
            if pattern in message_lower:
                # For "how do I create" type questions, prioritize ask_question
                # unless it's purely about creating without any question
                if "how" in message_lower or "what" in message_lower or "?" in message_lower:
                    intent = IntentType.ASK_QUESTION
                    break
        
        # Create workflow patterns
        if intent == IntentType.UNKNOWN:
            create_patterns = [
                "create a", "build a", "make a", "generate a", "new workflow",
                "new chatbot", "new bot", "design a workflow"
            ]
            
            for pattern in create_patterns:
                if pattern in message_lower:
                    intent = IntentType.CREATE_WORKFLOW
                    break
        
        # Modify workflow patterns  
        if intent == IntentType.UNKNOWN:
            modify_patterns = [
                "modify", "update", "change", "add", "remove", "edit",
                "extend", "improve", "enhance", "fix", "existing workflow"
            ]
            
            for pattern in modify_patterns:
                if pattern in message_lower:
                    intent = IntentType.MODIFY_WORKFLOW
                    break
        
        # Determine complexity
        complexity = ComplexityType.SIMPLE
        
        # Complex indicators
        complex_indicators = [
            "multiple", "several", "many", "complex", "advanced",
            "authentication", "authorization", "retry", "error handling",
            "notification", "webhook", "api", "custom code",
            "multiple knowledge bases", "multiple kb"
        ]
        
        # Medium indicators
        medium_indicators = [
            "knowledge base", "knowledge base search", "dataset",
            "conditional", "if else", "logic", "search"
        ]
        
        complex_count = sum(1 for p in complex_indicators if p in message_lower)
        medium_count = sum(1 for p in medium_indicators if p in message_lower)
        
        if complex_count >= 2 or "retry" in message_lower:
            complexity = ComplexityType.COMPLEX
        elif medium_count >= 2 or complex_count >= 1:
            complexity = ComplexityType.MEDIUM
        
        # Check for explicit complexity indicators
        if "simple" in message_lower:
            complexity = ComplexityType.SIMPLE
        elif "complex" in message_lower:
            complexity = ComplexityType.COMPLEX
        
        return IntentResult(
            intent=intent,
            complexity=complexity,
            requirements=message,
            confidence=0.5  # Lower confidence for rule-based
        )
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
