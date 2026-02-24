import { Schema, getMongoModel } from '../../common/mongo';

export const AIWorkflowSessionCollectionName = 'aiWorkflowSessions';

// Question type
const QuestionSchema = new Schema(
  {
    id: String,
    question: String,
    options: [String],
    type: { type: String, enum: ['choice', 'text'], default: 'text' }
  },
  { _id: false }
);

// Session schema
const AIWorkflowSessionSchema = new Schema(
  {
    sessionId: { type: String, required: true, index: true },
    teamId: { type: String, required: true, index: true },
    userId: { type: String, index: true },
    messages: [
      {
        role: { type: String, enum: ['user', 'assistant'] },
        content: String,
        timestamp: { type: Date, default: Date.now }
      }
    ],
    context: {
      mode: { type: String, enum: ['create', 'optimize'], default: 'create' },
      workflowId: String,
      questions: [QuestionSchema]
    },
    status: {
      type: String,
      enum: ['active', 'completed', 'expired'],
      default: 'active'
    },
    metadata: {
      generatedWorkflow: {
        nodes: { type: Schema.Types.Mixed },
        edges: { type: Schema.Types.Mixed }
      }
    }
  },
  {
    timestamps: true
  }
);

AIWorkflowSessionSchema.index({ teamId: 1, updatedAt: -1 });

export const MongoAIWorkflowSession = getMongoModel<any>(
  AIWorkflowSessionCollectionName,
  AIWorkflowSessionSchema
);
