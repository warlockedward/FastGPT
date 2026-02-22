import { connectionMongo, getMongoModel } from '../../../common/mongo';
const { Schema } = connectionMongo;

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
  createdAt: {
    type: Date,
    default: () => new Date()
  },
  updatedAt: {
    type: Date,
    default: () => new Date()
  }
});

export const MongoAiWorkflowSession = getMongoModel(
  'aiWorkflowSession',
  AiWorkflowSessionSchema
);
