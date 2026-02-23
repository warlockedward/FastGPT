import { MongoAiWorkflowSession } from './sessionSchema';
import { getNanoid } from '@fastgpt/global/common/string/tools';
import type { StoreNodeItemType } from '@fastgpt/global/core/workflow/type/node';
import type { StoreEdgeItemType } from '@fastgpt/global/core/workflow/type/edge';

// Intent types for workflow generation
export type WorkflowIntentType =
  | 'create_workflow'
  | 'modify_workflow'
  | 'ask_question'
  | 'clarify'
  | 'unknown';

export type WorkflowComplexityType = 'simple' | 'medium' | 'complex';

// Workflow state type
export type WorkflowStateType = {
  nodes: StoreNodeItemType[];
  edges: StoreEdgeItemType[];
  intent: {
    type: WorkflowIntentType;
  };
  complexity: WorkflowComplexityType;
  requirements?: string;
  isValid: boolean;
  validationErrors: string[];
  version: number;
};

// Create a new AI workflow session
export const createSession = async (data: {
  teamId: string;
  tmbId: string;
  mode?: 'create' | 'optimize' | 'extend';
}) => {
  const session = await MongoAiWorkflowSession.create({
    ...data,
    sessionId: getNanoid(),
    status: 'active',
    messages: [],
    workflowState: {
      nodes: [],
      edges: [],
      intent: { type: 'unknown' },
      complexity: 'simple',
      isValid: false,
      validationErrors: [],
      version: 1
    }
  });
  return session;
};

// Add a message to the session
export const addMessage = async (
  sessionId: string,
  message: {
    role: 'user' | 'assistant';
    content: string;
    attachments?: string[];
  }
) => {
  const session = await MongoAiWorkflowSession.findOneAndUpdate(
    { sessionId },
    {
      $push: { messages: { ...message, timestamp: new Date() } },
      $set: { updatedAt: new Date() }
    },
    { new: true }
  );
  return session;
};

// Get a session by ID
export const getSession = async (sessionId: string) => {
  return MongoAiWorkflowSession.findOne({ sessionId });
};

// Update session status
export const updateSessionStatus = async (
  sessionId: string,
  status: 'active' | 'completed' | 'cancelled'
) => {
  return MongoAiWorkflowSession.findOneAndUpdate(
    { sessionId },
    { $set: { status, updatedAt: new Date() } },
    { new: true }
  );
};

// Update workflow state (intent, complexity, requirements)
export const updateWorkflowIntent = async (
  sessionId: string,
  intent: {
    type: WorkflowIntentType;
    complexity?: WorkflowComplexityType;
    requirements?: string;
  }
) => {
  const updateData: Record<string, any> = {
    'workflowState.intent.type': intent.type,
    updatedAt: new Date()
  };
  if (intent.complexity) {
    updateData['workflowState.complexity'] = intent.complexity;
  }
  if (intent.requirements) {
    updateData['workflowState.requirements'] = intent.requirements;
  }

  return MongoAiWorkflowSession.findOneAndUpdate(
    { sessionId },
    { $set: updateData },
    { new: true }
  );
};

// Update workflow nodes and edges
export const updateWorkflowNodes = async (
  sessionId: string,
  workflow: {
    nodes: StoreNodeItemType[];
    edges: StoreEdgeItemType[];
  }
) => {
  return MongoAiWorkflowSession.findOneAndUpdate(
    { sessionId },
    {
      $set: {
        'workflowState.nodes': workflow.nodes,
        'workflowState.edges': workflow.edges,
        'workflowState.version': 1, // Will be incremented by validation
        updatedAt: new Date()
      }
    },
    { new: true }
  );
};

// Set workflow validation result
export const setWorkflowValidation = async (
  sessionId: string,
  validation: {
    isValid: boolean;
    validationErrors: string[];
  }
) => {
  const session = await MongoAiWorkflowSession.findOne({ sessionId });
  if (!session) return null;

  const currentVersion = session.workflowState?.version || 1;

  return MongoAiWorkflowSession.findOneAndUpdate(
    { sessionId },
    {
      $set: {
        'workflowState.isValid': validation.isValid,
        'workflowState.validationErrors': validation.validationErrors,
        'workflowState.version': validation.isValid ? currentVersion + 1 : currentVersion,
        updatedAt: new Date()
      }
    },
    { new: true }
  );
};

// Get workflow state
export const getWorkflowState = async (sessionId: string): Promise<WorkflowStateType | null> => {
  const session = await MongoAiWorkflowSession.findOne({ sessionId });
  if (!session) return null;
  return session.workflowState as WorkflowStateType;
};

// Link generated workflow to app
export const linkGeneratedWorkflow = async (
  sessionId: string,
  appId: string
) => {
  return MongoAiWorkflowSession.findOneAndUpdate(
    { sessionId },
    {
      $set: {
        generatedWorkflowId: appId,
        status: 'completed',
        updatedAt: new Date()
      }
    },
    { new: true }
  );
};
