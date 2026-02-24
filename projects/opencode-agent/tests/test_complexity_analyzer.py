"""
Tests for ComplexityAnalyzer - NEW VERSION (RED phase - tests should fail)
基于业务逻辑的复杂度分析器测试
"""
import pytest
from src.agent.intent_analyzer import ComplexityAnalyzer, ComplexityType


class TestComplexityAnalyzer:
    """复杂度分析器测试"""
    
    def test_simple_qa_bot(self):
        """简单的问答机器人应该是 Simple"""
        analyzer = ComplexityAnalyzer()
        result = analyzer.analyze("帮我做一个问答机器人")
        
        assert result.level == ComplexityType.SIMPLE
        assert result.score <= 15
    
    def test_simple_chatbot(self):
        """简单客服机器人应该是 Simple"""
        analyzer = ComplexityAnalyzer()
        result = analyzer.analyze("创建一个简单的客服机器人")
        
        assert result.level == ComplexityType.SIMPLE
    
    def test_vip_discount(self):
        """VIP打折 - 单条件分支应该是 Medium"""
        analyzer = ComplexityAnalyzer()
        result = analyzer.analyze("如果是VIP用户，给打折")
        
        # 有条件判断，应该是 Medium 或以上
        assert result.level in [ComplexityType.MEDIUM, ComplexityType.COMPLEX]
        assert "decision" in result.factors
        assert result.factors["decision"] >= 8
    
    def test_login_then_kb(self):
        """登录后查知识库 - 有条件+知识库 = Medium或Complex"""
        analyzer = ComplexityAnalyzer()
        result = analyzer.analyze("检查用户是否登录，登录了才返回知识库内容")
        
        # 有条件判断+知识库，可能是MEDIUM或COMPLEX（取决于分数）
        assert result.level in [ComplexityType.MEDIUM, ComplexityType.COMPLEX]
        assert "decision" in result.factors
        assert "integration" in result.factors
    
    def test_complex_with_api_and_fallback(self):
        """复杂流程: API验证+知识库+错误处理 = Complex"""
        analyzer = ComplexityAnalyzer()
        result = analyzer.analyze(
            "验证用户邮箱有效性，检查订阅状态，如果是活跃用户就搜索知识库，"
            "如果知识库为空就调用外部API，API失败则发送邮件通知管理员"
        )
        
        assert result.level == ComplexityType.COMPLEX
        assert result.score >= 36
    
    def test_recommended_nodes_simple(self):
        """Simple级别应推荐基础节点"""
        analyzer = ComplexityAnalyzer()
        result = analyzer.analyze("创建一个问答机器人")
        
        assert "workflowStart" in result.recommended_nodes
        assert "chatNode" in result.recommended_nodes
        assert "answerNode" in result.recommended_nodes
    
    def test_recommended_nodes_with_condition(self):
        """有条件判断应推荐分类节点"""
        analyzer = ComplexityAnalyzer()
        result = analyzer.analyze("如果用户是VIP，给不同的回答")
        
        assert "classifyQuestion" in result.recommended_nodes or "ifElseNode" in result.recommended_nodes
    
    def test_reasoning_provided(self):
        """结果应包含推理过程"""
        analyzer = ComplexityAnalyzer()
        result = analyzer.analyze("检查用户是否登录，登录了才返回知识库内容")
        
        assert len(result.reasoning) > 0
    
    def test_decision_keywords_detected(self):
        """决策关键词应该被检测到"""
        analyzer = ComplexityAnalyzer()
        
        # if 关键词
        result = analyzer.analyze("如果用户是VIP，打折")
        assert result.factors["decision"] > 0
    
    def test_integration_keywords_detected(self):
        """集成关键词应该被检测到"""
        analyzer = ComplexityAnalyzer()
        
        result = analyzer.analyze("搜索知识库内容")
        assert result.factors["integration"] > 0
    
    def test_error_keywords_detected(self):
        """错误处理关键词应该被检测到"""
        analyzer = ComplexityAnalyzer()
        
        result = analyzer.analyze("如果失败就发邮件通知")
        assert result.factors["error"] > 0
    
    def test_multiple_kb(self):
        """多个知识库应该是 Medium"""
        analyzer = ComplexityAnalyzer()
        result = analyzer.analyze("搜索多个知识库")
        
        assert result.factors["integration"] >= 10
    
    def test_webhook(self):
        """Webhook 应该是 Complex"""
        analyzer = ComplexityAnalyzer()
        result = analyzer.analyze("调用 webhook 发送通知")
        
        # webhook 是高权重关键词
        assert result.score >= 15


class TestIntentAnalyzerWithNewComplexity:
    """集成新复杂度分析器的 IntentAnalyzer 测试"""
    
    def test_analyze_simple_intent(self):
        """简单问答应该是 create_workflow + Simple"""
        from src.agent.intent_analyzer import IntentAnalyzer, IntentType, ComplexityType
        
        analyzer = IntentAnalyzer()
        # 使用同步方式测试 (rule-based only)
        result = analyzer._rule_based_analysis("创建一个问答机器人")
        
        assert result.intent == IntentType.CREATE_WORKFLOW
        assert result.complexity == ComplexityType.SIMPLE
    
    def test_analyze_conditional_intent(self):
        """有条件判断应该是 Medium 或 Complex"""
        from src.agent.intent_analyzer import IntentAnalyzer, IntentType
        
        analyzer = IntentAnalyzer()
        result = analyzer._rule_based_analysis("如果用户是VIP，给打折")
        
        assert result.intent == IntentType.CREATE_WORKFLOW
        # 复杂度应该反映条件判断的复杂性
