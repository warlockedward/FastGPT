"""
State Machine - Workflow generation state management
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json


class GenerationState(str, Enum):
    IDLE = "idle"
    CLARIFYING = "clarifying"
    GENERATING = "generating"
    VALIDATING = "validating"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    ERROR = "error"


class ClarificationQuestion(BaseModel):
    """A question for user clarification"""

    id: str
    question: str
    options: Optional[List[str]] = None
    required: bool = True


class WorkflowState(BaseModel):
    """State of workflow generation"""

    session_id: str
    state: GenerationState
    user_intent: str
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    clarification_questions: List[ClarificationQuestion] = []
    validation_issues: List[Dict[str, Any]] = []
    low_confidence_mappings: List[Dict[str, Any]] = []
    error_message: Optional[str] = None
    retry_count: int = 0


class StateMachine:
    STATE_TRANSITIONS = {
        GenerationState.IDLE: [GenerationState.CLARIFYING, GenerationState.GENERATING],
        GenerationState.CLARIFYING: [GenerationState.GENERATING, GenerationState.IDLE],
        GenerationState.GENERATING: [GenerationState.VALIDATING, GenerationState.ERROR],
        GenerationState.VALIDATING: [
            GenerationState.REVIEWING,
            GenerationState.GENERATING,
            GenerationState.ERROR,
        ],
        GenerationState.REVIEWING: [
            GenerationState.COMPLETED,
            GenerationState.GENERATING,
            GenerationState.ERROR,
        ],
        GenerationState.COMPLETED: [GenerationState.IDLE],
        GenerationState.ERROR: [GenerationState.IDLE, GenerationState.GENERATING],
    }

    def __init__(self):
        self.states: Dict[str, WorkflowState] = {}

    def create_session(self, session_id: str, user_intent: str) -> WorkflowState:
        """Create a new session state"""
        state = WorkflowState(
            session_id=session_id, state=GenerationState.IDLE, user_intent=user_intent
        )
        self.states[session_id] = state
        return state

    def get_state(self, session_id: str) -> Optional[WorkflowState]:
        """Get current state for a session"""
        return self.states.get(session_id)

    def can_transition(self, session_id: str, new_state: GenerationState) -> bool:
        """Check if state transition is valid"""
        current = self.get_state(session_id)
        if not current:
            return False

        allowed = self.STATE_TRANSITIONS.get(current.state, [])
        return new_state in allowed

    def transition(
        self, session_id: str, new_state: GenerationState, **kwargs
    ) -> WorkflowState:
        """Transition to a new state"""
        if not self.can_transition(session_id, new_state):
            raise ValueError(
                f"Invalid transition from {self.get_state(session_id).state} to {new_state}"
            )

        current = self.get_state(session_id)
        if not current:
            raise ValueError(f"Session {session_id} not found")

        current.state = new_state

        # Update state with additional data
        if "nodes" in kwargs:
            current.nodes = kwargs["nodes"]
        if "edges" in kwargs:
            current.edges = kwargs["edges"]
        if "questions" in kwargs:
            current.clarification_questions = kwargs["questions"]
        if "validation_issues" in kwargs:
            current.validation_issues = kwargs["validation_issues"]
        if "low_confidence_mappings" in kwargs:
            current.low_confidence_mappings = kwargs["low_confidence_mappings"]
        if "error" in kwargs:
            current.error_message = kwargs["error"]

        if new_state == GenerationState.ERROR:
            current.retry_count += 1

        return current

    def start_clarification(
        self, session_id: str, questions: List[ClarificationQuestion]
    ) -> WorkflowState:
        """Start clarification phase"""
        return self.transition(
            session_id, GenerationState.CLARIFYING, questions=questions
        )

    def start_generation(self, session_id: str) -> WorkflowState:
        """Start generation phase"""
        return self.transition(session_id, GenerationState.GENERATING)

    def start_validation(
        self, session_id: str, nodes: List, edges: List
    ) -> WorkflowState:
        """Start validation phase"""
        return self.transition(
            session_id, GenerationState.VALIDATING, nodes=nodes, edges=edges
        )

    def start_review(
        self,
        session_id: str,
        validation_issues: List[Dict],
        low_confidence_mappings: List[Dict],
    ) -> WorkflowState:
        """Start review phase"""
        return self.transition(
            session_id,
            GenerationState.REVIEWING,
            validation_issues=validation_issues,
            low_confidence_mappings=low_confidence_mappings,
        )

    def complete(self, session_id: str) -> WorkflowState:
        """Mark workflow as completed"""
        return self.transition(session_id, GenerationState.COMPLETED)

    def error(self, session_id: str, error_message: str) -> WorkflowState:
        """Mark workflow as error"""
        return self.transition(session_id, GenerationState.ERROR, error=error_message)

    def reset(self, session_id: str) -> WorkflowState:
        """Reset to idle state"""
        return self.transition(session_id, GenerationState.IDLE)

    def retry(self, session_id: str) -> WorkflowState:
        """Retry generation after error"""
        return self.transition(session_id, GenerationState.GENERATING)

    def is_locked(self, session_id: str) -> bool:
        """Check if canvas should be locked"""
        state = self.get_state(session_id)
        if not state:
            return False

        return state.state in [GenerationState.GENERATING, GenerationState.VALIDATING]

    def needs_user_confirmation(self, session_id: str) -> bool:
        """Check if needs user confirmation"""
        state = self.get_state(session_id)
        if not state:
            return False

        return (
            state.state == GenerationState.REVIEWING
            and len(state.low_confidence_mappings) > 0
        ) or (
            state.state == GenerationState.CLARIFYING
            and len(state.clarification_questions) > 0
        )

    def get_lock_info(self, session_id: str) -> Dict[str, Any]:
        """Get lock information for UI"""
        state = self.get_state(session_id)
        if not state:
            return {"locked": False}

        return {
            "locked": self.is_locked(session_id),
            "state": state.state.value,
            "message": self._get_lock_message(state),
            "needs_confirmation": self.needs_user_confirmation(session_id),
            "confirmation_items": self._get_confirmation_items(state),
        }

    def _get_lock_message(self, state: WorkflowState) -> str:
        """Get lock message for current state"""
        messages = {
            GenerationState.IDLE: "",
            GenerationState.CLARIFYING: "需要确认一些信息",
            GenerationState.GENERATING: "正在生成工作流...",
            GenerationState.VALIDATING: "正在验证工作流...",
            GenerationState.REVIEWING: "请确认以下内容",
            GenerationState.COMPLETED: "",
            GenerationState.ERROR: f"发生错误: {state.error_message}",
        }
        return messages.get(state.state, "")

    def _get_confirmation_items(self, state: WorkflowState) -> List[Dict]:
        """Get items that need confirmation"""
        items = []

        if state.state == GenerationState.CLARIFYING:
            for q in state.clarification_questions:
                items.append(
                    {
                        "type": "clarification",
                        "id": q.id,
                        "question": q.question,
                        "options": q.options,
                    }
                )

        if state.state == GenerationState.REVIEWING:
            for m in state.low_confidence_mappings:
                items.append(
                    {
                        "type": "mapping",
                        "source": m.get("source_node_id"),
                        "source_var": m.get("source_variable"),
                        "target": m.get("target_node_id"),
                        "target_var": m.get("target_variable"),
                        "confidence": m.get("confidence"),
                    }
                )

            for issue in state.validation_issues:
                if issue.get("severity") == "warning":
                    items.append(
                        {
                            "type": "validation_warning",
                            "message": issue.get("message"),
                            "suggestion": issue.get("suggestion"),
                        }
                    )

        return items

    def export_state(self, session_id: str) -> Optional[str]:
        """Export state as JSON"""
        state = self.get_state(session_id)
        if not state:
            return None

        return json.dumps(state.model_dump(), ensure_ascii=False, indent=2)

    def import_state(self, session_id: str, json_str: str) -> WorkflowState:
        """Import state from JSON"""
        data = json.loads(json_str)
        state = WorkflowState(**data)
        self.states[session_id] = state
        return state

    def cleanup(self, session_id: str):
        """Remove session state"""
        if session_id in self.states:
            del self.states[session_id]


state_machine = StateMachine()
