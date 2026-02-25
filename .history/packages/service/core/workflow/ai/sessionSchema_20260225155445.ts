import { connectionMongo, getMongoModel } from '../../../common/mongo';
const { Schema } = connectionMongo;

export type AiWorkflowSessionSchemaType = {
  _id: string;
  teamId: string;
  tmbId: string;
  sessionId: string;
  mode: 'create' | 'optimize' | 'extend';
  status: 'active' | 'completed' | 'cancelled';
  messages: {
    role: 'user' | 'assistant';
    content: string;
    attachments?: string[];
    timestamp: Date;
  }[];
  generatedWorkflowId?: string;
  workflowState: {
    nodes: any[];
    edges: any[];
    intent: {
      type: 'create_workflow' | 'modify_workflow' | 'ask_question' | 'clarify' | 'unknown';
    };
    complexity: 'simple' | 'medium' | 'complex';
    requirements?: string;
    isValid: boolean;
    validationErrors: string[];
    version: number;
  };
  createdAt: Date;
  updatedAt: Date;
};

const ChatMessageSchema = new Schema({
  role: {
    type: String,
    enum: ['user', 'assistant'],
    required: true
  },
  content: {
    type: String,
    required: true
  },
  attachments: {
    type: [String],
    default: []
  },
  timestamp: {
    type: Date,
    default: () => new Date()
  }
});

// Workflow state schemas for tracking generated workflow
const WorkflowNodeSchema = new Schema(
  {
    nodeId: { type: String, required: true },
    flowNodeType: { type: String, required: true },
    name: { type: String, required: true },
    position: {
      x: { type: Number, default: 0 },
      y: { type: Number, default: 0 }
    },
    inputs: { type: Array, default: [] },
    outputs: { type: Array, default: [] }
  },
  { _id: false, strict: false }
);

const WorkflowEdgeSchema = new Schema(
  {
    source: { type: String, required: true },
    sourceHandle: { type: String, required: true },
    target: { type: String, required: true },
    targetHandle: { type: String, required: true }
  },
  { _id: false, strict: false }
);

const WorkflowStateSchema = new Schema(
  {
    nodes: { type: [WorkflowNodeSchema], default: [] },
    edges: { type: [WorkflowEdgeSchema], default: [] },
    intent: {
      type: {
        type: String,
        enum: ['create_workflow', 'modify_workflow', 'ask_question', 'clarify', 'unknown']
      },
      required: true
    },
    complexity: {
      type: String,
      enum: ['simple', 'medium', 'complex'],
      default: 'simple'
    },
    requirements: { type: String },
    isValid: { type: Boolean, default: false },
    validationErrors: { type: [String], default: [] },
    version: { type: Number, default: 1 }
  },
  { _id: false }
);

const AiWorkflowSessionSchema = new Schema({
  teamId: {
    type: String,
    required: true
  },
  tmbId: {
    type: String,
    required: true
  },
  sessionId: {
    type: String,
    required: true,
    index: true
  },
  mode: {
    type: String,
    enum: ['create', 'optimize', 'extend'],
    default: 'create'
  },
  status: {
    type: String,
    enum: ['active', 'completed', 'cancelled'],
    default: 'active'
  },
  messages: {
    type: [ChatMessageSchema],
    default: []
  },
  generatedWorkflowId: {
    type: String
  },
  // Workflow state tracking for AI-generated workflows
  workflowState: {
    type: WorkflowStateSchema,
    default: () => ({
      nodes: [],
      edges: [],
      intent: { type: 'unknown' },
      complexity: 'simple',
      isValid: false,
      validationErrors: [],
      version: 1
    })
  },
  createdAt: {
    type: Date,
    default: () => new Date()
  },
  updatedAt: {
    type: Date,
    default: () => new Date()
  }
});

export const MongoAiWorkflowSession = getMongoModel<AiWorkflowSessionSchemaType>(
  'aiWorkflowSession',
  AiWorkflowSessionSchema
);
