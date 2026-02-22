import { connectionMongo, getMongoModel } from '../../../common/mongo';
const { Schema } = connectionMongo;

const PluginSchema = new Schema({
  teamId: {
    type: String,
    required: true
  },
  name: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  },
  code: {
    type: String,
    required: true
  },
  status: {
    type: String,
    enum: ['draft', 'published', 'archived'],
    default: 'draft'
  },
  version: {
    type: String,
    default: '1.0.0'
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

export const MongoAiPlugin = getMongoModel('aiPlugin', PluginSchema);
