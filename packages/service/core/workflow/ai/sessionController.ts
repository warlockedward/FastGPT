import { MongoAiWorkflowSession } from './sessionSchema';
import { getNanoid } from '@fastgpt/global/common/string/tools';

export const createSession = async (data: {
  teamId: string;
  tmbId: string;
  mode?: 'create' | 'optimize' | 'extend';
}) => {
  const session = await MongoAiWorkflowSession.create({
    ...data,
    sessionId: getNanoid(),
    status: 'active',
    messages: []
  });
  return session;
};

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

export const getSession = async (sessionId: string) => {
  return MongoAiWorkflowSession.findOne({ sessionId });
};

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
