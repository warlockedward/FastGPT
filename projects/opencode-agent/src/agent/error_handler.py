"""
Error Handler - User-friendly error messages with suggestions for AI Workflow Generator
"""
from typing import Optional, List, Dict, Any
from enum import Enum


class ErrorCategory(str, Enum):
    """Categories of errors for better user feedback"""
    VALIDATION = "validation"
    LLM = "llm"
    WORKFLOW = "workflow"
    SESSION = "session"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    UNKNOWN = "unknown"


class UserFriendlyError:
    """Error with user-friendly message and suggestions"""
    
    def __init__(
        self,
        category: ErrorCategory,
        user_message: str,
        technical_error: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        can_retry: bool = False
    ):
        self.category = category
        self.user_message = user_message
        self.technical_error = technical_error
        self.suggestions = suggestions or []
        self.can_retry = can_retry
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "message": self.user_message,
            "technical": self.technical_error,
            "suggestions": self.suggestions,
            "canRetry": self.can_retry
        }


class WorkflowErrorHandler:
    """Handles errors with user-friendly messages and suggestions"""
    
    # Error mappings with suggestions (lowercase keys)
    ERROR_MAPPINGS = {
        # Validation errors
        "workflow must have a workflowstart node": UserFriendlyError(
            category=ErrorCategory.VALIDATION,
            user_message="Your workflow needs a starting point.",
            suggestions=[
                "Add a 'Workflow Start' node as the entry point",
                "This is required for the workflow to run"
            ],
            can_retry=True
        ),
        "workflow must have at least one node": UserFriendlyError(
            category=ErrorCategory.VALIDATION,
            user_message="Your workflow is empty.",
            suggestions=[
                "Add at least one node to create a workflow",
                "Try starting with a simple chat node"
            ],
            can_retry=True
        ),
        
        # LLM errors
        "timeout": UserFriendlyError(
            category=ErrorCategory.LLM,
            user_message="The AI took too long to respond. Please try again.",
            suggestions=[
                "Try simplifying your request",
                "Reduce the complexity of your workflow",
                "Check your internet connection"
            ],
            can_retry=True
        ),
        "rate limit": UserFriendlyError(
            category=ErrorCategory.LLM,
            user_message="Too many requests. Please wait a moment.",
            suggestions=[
                "Wait a few seconds before trying again",
                "Consider reducing the frequency of requests"
            ],
            can_retry=True
        ),
        "invalid api key": UserFriendlyError(
            category=ErrorCategory.AUTHENTICATION,
            user_message="There's an issue with your API configuration.",
            technical_error="Invalid API key",
            suggestions=[
                "Check your FastGPT API key in settings",
                "Ensure you have access to the AI services"
            ],
            can_retry=False
        ),
        "authentication failed": UserFriendlyError(
            category=ErrorCategory.AUTHENTICATION,
            user_message="Couldn't verify your access. Please check your credentials.",
            technical_error="Authentication failed",
            suggestions=[
                "Log out and log back in",
                "Check your API key is correct"
            ],
            can_retry=False
        ),
        
        # Workflow errors
        "invalid node type": UserFriendlyError(
            category=ErrorCategory.WORKFLOW,
            user_message="One of the components isn't recognized.",
            suggestions=[
                "Try using standard node types like Chat, Knowledge Base Search, or Answer",
                "Check that all node types are correctly spelled"
            ],
            can_retry=True
        ),
        "failed to generate workflow": UserFriendlyError(
            category=ErrorCategory.WORKFLOW,
            user_message="Couldn't create your workflow. Try a simpler description.",
            suggestions=[
                "Break down your request into smaller parts",
                "Start with a simple workflow and add complexity gradually"
            ],
            can_retry=True
        ),
        
        # Session errors
        "session not found": UserFriendlyError(
            category=ErrorCategory.SESSION,
            user_message="Your conversation session was lost. Let's start fresh!",
            suggestions=[
                "Start a new conversation",
                "Your previous progress may need to be recreated"
            ],
            can_retry=True
        ),
        
        # Network errors
        "connection": UserFriendlyError(
            category=ErrorCategory.NETWORK,
            user_message="Couldn't connect to the server.",
            suggestions=[
                "Check your internet connection",
                "Try refreshing the page",
                "The service might be temporarily unavailable"
            ],
            can_retry=True
        ),
        "network error": UserFriendlyError(
            category=ErrorCategory.NETWORK,
            user_message="Something went wrong with the connection.",
            suggestions=[
                "Check your internet connection",
                "Try again in a few moments"
            ],
            can_retry=True
        ),
    }
    
    # Default error for unknown errors
    DEFAULT_ERROR = UserFriendlyError(
        category=ErrorCategory.UNKNOWN,
        user_message="Something unexpected happened. Please try again.",
        suggestions=[
            "Try refreshing the page",
            "If the problem persists, try a simpler request"
        ],
        can_retry=True
    )
    
    @classmethod
    def handle_error(cls, error: Exception) -> UserFriendlyError:
        """Convert an exception to a user-friendly error"""
        error_str = str(error).lower()
        
        # Try to match error to known patterns
        for pattern, friendly_error in cls.ERROR_MAPPINGS.items():
            if pattern in error_str:
                # Copy the error and attach the technical message
                return UserFriendlyError(
                    category=friendly_error.category,
                    user_message=friendly_error.user_message,
                    technical_error=str(error),
                    suggestions=friendly_error.suggestions,
                    can_retry=friendly_error.can_retry
                )
        
        # Return default error with technical details
        return UserFriendlyError(
            category=ErrorCategory.UNKNOWN,
            user_message=cls.DEFAULT_ERROR.user_message,
            technical_error=str(error),
            suggestions=cls.DEFAULT_ERROR.suggestions,
            can_retry=cls.DEFAULT_ERROR.can_retry
        )
    
    @classmethod
    def handle_validation_error(cls, errors: List[str]) -> UserFriendlyError:
        """Handle workflow validation errors"""
        combined_message = " ".join(errors)
        
        # Check for specific patterns (case insensitive)
        if "workflowstart" in combined_message.lower():
            return cls.ERROR_MAPPINGS["workflow must have a workflowstart node"]
        
        return UserFriendlyError(
            category=ErrorCategory.VALIDATION,
            user_message="There are some issues with your workflow configuration.",
            technical_error=combined_message,
            suggestions=[
                "Review the error messages above",
                "Ensure all required nodes are connected",
                "Check that node inputs are properly configured"
            ],
            can_retry=True
        )
    
    @classmethod
    def handle_llm_error(cls, error: Exception) -> UserFriendlyError:
        """Handle LLM-specific errors"""
        error_str = str(error).lower()
        
        if "timeout" in error_str:
            return cls.ERROR_MAPPINGS["timeout"]
        if "rate limit" in error_str:
            return cls.ERROR_MAPPINGS["rate limit"]
        if "api key" in error_str or "unauthorized" in error_str:
            return cls.ERROR_MAPPINGS["invalid api key"]
        
        return cls.handle_error(error)


def format_error_response(error: Exception) -> Dict[str, Any]:
    """Format error for API response"""
    friendly_error = WorkflowErrorHandler.handle_error(error)
    return friendly_error.to_dict()


def format_validation_response(errors: List[str]) -> Dict[str, Any]:
    """Format validation errors for API response"""
    friendly_error = WorkflowErrorHandler.handle_validation_error(errors)
    return friendly_error.to_dict()
