"""
IntentAnalyzer - Analyzes user messages to determine intent and extract workflow requirements
基于业务逻辑的复杂度评估系统 v2.0
"""
import json
import os
import re
from enum import Enum
from typing import Optional, List, Dict
from dataclasses import dataclass
from pydantic import BaseModel, Field
import httpx


# ============================================================
# 意图类型
# ============================================================
class IntentType(str, Enum):
    """Intent types for workflow generation"""
    CREATE_WORKFLOW = "create_workflow"
    MODIFY_WORKFLOW = "modify_workflow"
    ASK_QUESTION = "ask_question"
    CLARIFY = "clarify"
    UNKNOWN = "unknown"


# ============================================================
# 复杂度等级 (基于业务逻辑)
# ============================================================
class ComplexityType(str, Enum):
    """
    Workflow complexity levels based on BUSINESS LOGIC, not node count:
    
    - SIMPLE: 线性流程，无条件分支，无外部依赖
    - MEDIUM: 有分支或简单依赖，1-2个判断
    - COMPLEX: 多分支+外部集成+错误处理，3+判断或多个服务
    """
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


# ============================================================
# 复杂度分析结果
# ============================================================
@dataclass
class ComplexityResult:
    """Result of complexity analysis"""
    level: ComplexityType
    score: int
    factors: Dict[str, int]  # decision, integration, data, error
    reasoning: List[str]
    recommended_nodes: List[str]


# ============================================================
# 复杂度分析器 v2.0
# ============================================================
class ComplexityAnalyzer:
    """
    基于业务逻辑的工作流复杂度分析器
    
    核心洞见: 复杂度来自决策逻辑的嵌套深度,不是节点数量
    """
    
    # 决策类关键词 (权重最高 - 最高40分)
    DECISION_KEYWORDS = {
        # 基础条件 (中英文)
        r'\bif\b': 10, r'\bwhen\b': 10, r'\bwhether\b': 12,
        r'\bcheck\b': 8, r'\bverify\b': 8, r'\bvalidate\b': 8,
        r'如果': 12, r'假如': 10, r'要是': 10, r'万一': 10,
        r'判断': 10, r'检查': 8, r'验证': 8, r'查看': 8,
        r'是否': 12, r'有没有': 10, r'有没有': 10,
        r'当': 10, r'只要': 10, r'除非': 12,
        
        # 权限/角色
        r'\bvip\b': 12, r'\bpremium\b': 12, r'\bgold\b': 12,
        r'\badmin\b': 15, r'\bpermission\b': 15, r'\bauthorized\b': 15,
        r'\bauthenticate\b': 15, r'\blogin\b': 10, r'\blogged in\b': 12,
        r'\bsubscribed\b': 10, r'\bsubscription\b': 12,
        r'会员': 12, r'VIP': 12, r'付费': 10, r'管理员': 15,
        r'权限': 15, r'授权': 15, r'登录': 10, r'已登录': 12,
        r'订阅': 12, r'订阅状态': 15,
        
        # 流程控制
        r'\band then\b': 15, r'\bafter that\b': 12, r'\bthen\b': 8,
        r'\bfirst\b': 8, r'\bbefore\b': 10, r'\bdepending on\b': 18,
        r'然后': 12, r'之后': 10, r'接着': 10, r'首先': 8, r'之前': 10,
        r'取决于': 18, r'根据': 12, r'依据': 12,
        
        # 条件组合
        r'\bor\b': 10, r'\band\b': 10, r'\botherwise\b': 12,
        r'\bif else\b': 15, r'\bif not\b': 15,
        r'或者': 10, r'并且': 10, r'而且': 10, r'否则': 12,
        r'如果...否则': 15, r'要么...要么': 12,
        
        # 状态检查
        r'\bavailable\b': 8, r'\bexist\b': 8, r'\bfound\b': 8,
        r'可用': 8, r'存在': 8, r'有': 5, r'没有': 8,
        r'为空': 10, r'是空的': 10, r'没有内容': 10,
    }
    
    # 外部集成关键词 (最高35分)
    INTEGRATION_KEYWORDS = {
        # 知识库
        r'\bknowledge base\b': 8, r'\bkb\b': 8, r'\bdataset\b': 6,
        r'\bvector store\b': 8, r'\bdocuments\b': 5,
        r'\bmultiple kb\b': 15, r'\bseveral sources\b': 15, r'\bvarious sources\b': 15,
        # 中文知识库
        r'知识库': 8, r'向量库': 6, r'数据集': 6, r'文档库': 5,
        r'多个知识库': 15, r'多个库': 12, r'搜索知识库': 10,
        
        # 外部API
        r'\bapi\b': 18, r'\bhttp\b': 18, r'\bendpoint\b': 15,
        r'\bwebhook\b': 25, r'\bcallback\b': 20,
        r'\bthird[\s-]?party\b': 20, r'\bintegrate\b': 18,
        r'\bexternal\b': 15,
        
        # 认证服务
        r'\boauth\b': 20, r'\bsaml\b': 20, r'\bjwt\b': 18,
    }
    
    # 数据处理关键词 (最高20分)
    DATA_KEYWORDS = {
        r'\bsearch\b': 5, r'\bquery\b': 5, r'\bretrieve\b': 5,
        r'\baggregate\b': 12, r'\bcombine\b': 12, r'\bmerge\b': 12,
        r'\btransform\b': 10, r'\bconvert\b': 10, r'\bparse\b': 10,
        r'\banalyze\b': 18, r'\bsummarize\b': 18, r'\bextract\b': 12,
        r'\bclassify\b': 15, r'\bcategorize\b': 15,
    }
    
    # 错误处理关键词 (最高25分)
    ERROR_KEYWORDS = {
        r'\bretry\b': 8, r'\btry again\b': 10,
        r'\bfallback\b': 15, r'\bbackup\b': 12, r'\balternative\b': 12,
        r'\bif fail\b': 15, r'\bon error\b': 15, r'\bif error\b': 15,
        r'\bcatch\b': 12, r'\bexception\b': 12,
        r'\bnotify\b': 18, r'\balert\b': 18, r'\bsend notification\b': 20,
        r'\bemail\b': 15, r'\bsms\b': 18, r'\bmessage\b': 10,
        # 中文错误处理
        r'失败': 12, r'错误': 10, r'异常': 10, r'重试': 8,
        r'发送通知': 18, r'发邮件': 15, r'发短信': 18, r'报错': 10,
    }
    
    def __init__(self):
        self.all_keywords = {}
        self.all_keywords.update(self.DECISION_KEYWORDS)
        self.all_keywords.update(self.INTEGRATION_KEYWORDS)
        self.all_keywords.update(self.DATA_KEYWORDS)
        self.all_keywords.update(self.ERROR_KEYWORDS)
    
    def analyze(self, message: str) -> ComplexityResult:
        """分析用户输入的复杂度"""
        message_lower = message.lower()
        
        # 1. 计算各维度分数
        decision_score = self._calculate_score(message_lower, self.DECISION_KEYWORDS)
        integration_score = self._calculate_score(message_lower, self.INTEGRATION_KEYWORDS)
        data_score = self._calculate_score(message_lower, self.DATA_KEYWORDS)
        error_score = self._calculate_score(message_lower, self.ERROR_KEYWORDS)
        
        factors = {
            "decision": decision_score,
            "integration": integration_score,
            "data": data_score,
            "error": error_score,
        }
        
        # 2. 计算总分 (带权重)
        total_score = (
            decision_score * 1.0 +    # 决策最重要
            integration_score * 0.9 +  # 外部集成次之
            data_score * 0.7 +         # 数据处理
            error_score * 0.8         # 错误处理
        )
        
        # 3. 确定复杂度等级
        level = self._get_complexity_level(total_score)
        
        # 4. 生成推理过程
        reasoning = self._generate_reasoning(factors)
        
        # 5. 推荐节点
        recommended_nodes = self._recommend_nodes(factors)
        
        return ComplexityResult(
            level=level,
            score=round(total_score),
            factors=factors,
            reasoning=reasoning,
            recommended_nodes=recommended_nodes,
        )
    
    def _calculate_score(self, text: str, keywords: Dict[str, int]) -> int:
        """计算某个维度的分数"""
        score = 0
        seen_positions = set()  # 避免重叠匹配
        
        for pattern, weight in keywords.items():
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                start = match.start()
                if not any(start in range(s, e) for s, e in seen_positions):
                    score += weight
                    seen_positions.add((start, match.end()))
        
        return min(score, 40)  # 单维度最高40分
    
    def _get_complexity_level(self, score: float) -> ComplexityType:
        """根据分数确定复杂度等级"""
        if score <= 23:
            return ComplexityType.SIMPLE
        elif score <= 46:
            return ComplexityType.MEDIUM
        else:
            return ComplexityType.COMPLEX
    
    def _generate_reasoning(self, factors: Dict[str, int]) -> List[str]:
        """生成推理说明"""
        reasoning = []
        
        if factors["decision"] >= 10:
            reasoning.append("检测到条件分支逻辑")
        if factors["integration"] >= 15:
            reasoning.append("涉及外部服务集成")
        if factors["data"] >= 10:
            reasoning.append("需要进行数据处理")
        if factors["error"] >= 10:
            reasoning.append("需要错误处理机制")
            
        return reasoning if reasoning else ["简单的线性工作流"]
    
    def _recommend_nodes(self, factors: Dict[str, int]) -> List[str]:
        """根据复杂度推荐节点"""
        nodes = ["workflowStart"]
        
        # 决策相关节点
        if factors["decision"] >= 15:
            nodes.append("classifyQuestion")
            nodes.append("ifElseNode")
        elif factors["decision"] >= 8:
            nodes.append("classifyQuestion")
        
        # 数据/集成相关
        if factors["integration"] >= 15:
            nodes.append("httpRequest468")
        if factors["integration"] >= 5 or factors["data"] >= 5:
            nodes.append("datasetSearchNode")
        
        # 错误处理
        if factors["error"] >= 15:
            nodes.append("ifElseNode")
            nodes.append("httpRequest468")
        
        # 核心处理
        nodes.append("chatNode")
        nodes.append("answerNode")
        
        return nodes


# ============================================================
# 意图分析结果
# ============================================================
class IntentResult(BaseModel):
    """Result of intent analysis"""
    intent: IntentType
    complexity: ComplexityType
    complexity_score: int = 0
    complexity_factors: Dict[str, int] = {}
    complexity_reasoning: List[str] = []
    recommended_nodes: List[str] = []
    requirements: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# ============================================================
# 意图分析器
# ============================================================
class IntentAnalyzer:
    """Analyzes user messages to determine intent and extract workflow requirements"""
    
    SYSTEM_PROMPT = """You are an AI Workflow intent analyzer. Your task is to analyze user messages
and determine what they want to do with workflow creation.

Analyze the message and respond with a JSON object containing:
- intent: One of "create_workflow", "modify_workflow", "ask_question", "clarify", or "unknown"
- complexity: One of "simple", "medium", or "complex" (based on BUSINESS LOGIC complexity)
- requirements: A brief description of what the user wants

Complexity guidelines (based on DECISION LOGIC, not node count):
- "simple": Linear flow, no conditions, no external dependencies
- "medium": Has branches or simple dependencies, 1-2 conditions
- "complex": Multiple branches + external integration + error handling, 3+ conditions

Examples:
- "create a Q&A bot" → simple
- "if user is VIP, give discount" → medium (single condition)
- "verify email, check subscription, if active search KB, if empty try API, on error notify" → complex

Respond ONLY with valid JSON, no other text."""

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None, model: Optional[str] = None):
        self.base_url = base_url or os.environ.get("VLLM_BASE_URL", os.environ.get("FASTGPT_API_URL", "http://fastgpt:3000"))
        self.api_key = api_key or os.environ.get("VLLM_API_KEY", os.environ.get("FASTGPT_API_KEY", ""))
        self.model = model or os.environ.get("VLLM_MODEL", "Qwen3-235B-A22B-Thinking-2507")
        self.client = httpx.AsyncClient(timeout=60.0)
        self.complexity_analyzer = ComplexityAnalyzer()
    
    async def analyze(self, message: str) -> IntentResult:
        """
        Analyze a user message to determine intent and extract requirements.
        
        Args:
            message: The user's message
            
        Returns:
            IntentResult with intent, complexity, and requirements
        """
        # 使用新的复杂度分析器
        complexity_result = self.complexity_analyzer.analyze(message)
        
        # Try to use LLM for intent analysis
        try:
            intent_result = await self._analyze_intent_with_llm(message)
            # 合并复杂度信息
            intent_result.complexity = complexity_result.level
            intent_result.complexity_score = complexity_result.score
            intent_result.complexity_factors = complexity_result.factors
            intent_result.complexity_reasoning = complexity_result.reasoning
            intent_result.recommended_nodes = complexity_result.recommended_nodes
            return intent_result
        except Exception as e:
            # Fallback to rule-based analysis if LLM fails
            return self._rule_based_analysis(message, complexity_result)
    
    async def _analyze_intent_with_llm(self, message: str) -> IntentResult:
        """Use LLM to analyze the intent"""
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
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
        
        raise Exception("LLM response parsing failed")
    
    def _rule_based_analysis(self, message: str, complexity_result: ComplexityResult = None) -> IntentResult:
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
                if "how" in message_lower or "what" in message_lower or "?" in message_lower:
                    intent = IntentType.ASK_QUESTION
                    break
        
        # Create workflow patterns
        if intent == IntentType.UNKNOWN:
            create_patterns = [
                "create a", "build a", "make a", "generate a", "new workflow",
                "new chatbot", "new bot", "design a workflow",
                # 中文创建模式
                "创建", "制作", "做一个", "新建", "生成", "开发",
                # 条件描述也暗示创建工作流
                "如果", "假如", "要是", "当用户", "当用户是"
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
        
        # Use complexity analyzer result if available
        if complexity_result is None:
            complexity_result = self.complexity_analyzer.analyze(message)
        
        return IntentResult(
            intent=intent,
            complexity=complexity_result.level,
            complexity_score=complexity_result.score,
            complexity_factors=complexity_result.factors,
            complexity_reasoning=complexity_result.reasoning,
            recommended_nodes=complexity_result.recommended_nodes,
            requirements=message,
            confidence=0.5
        )
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
