import type { NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { ReadPermissionVal } from '@fastgpt/global/support/permission/constant';
import type { ApiRequestProps } from '@fastgpt/service/type/next';
import {
  getSession,
  addMessage,
  updateWorkflowNodes
} from '@fastgpt/service/core/workflow/ai/sessionController';

async function handler(req: ApiRequestProps, res: NextApiResponse) {
  const { teamId } = await authUserPer({
    req,
    authToken: true,
    per: ReadPermissionVal
  });

  const body = req.body;
  const { sessionId, answer, confirmed } = body;

  if (!sessionId) {
    return Promise.reject('sessionId is required');
  }

  // 1. Get and verify session
  const session = await getSession(sessionId);
  if (!session) {
    return Promise.reject('Session not found');
  }
  if (session.teamId !== teamId) {
    return Promise.reject('Permission denied');
  }

  const opencodeApiUrl = process.env.OPENCODE_API_URL;
  if (!opencodeApiUrl) {
    return Promise.reject('OPENCODE_API_URL is not configured');
  }

  // 2. Add user message to session
  await addMessage(sessionId, {
    role: 'user',
    content: answer || (confirmed ? 'Confirmed' : 'Rejected')
  });

  try {
    const response = await fetch(`${opencodeApiUrl}/api/ai-workflow/confirm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.OPENCODE_API_KEY || ''}`
      },
      body: JSON.stringify({
        sessionId,
        answer,
        confirmed: confirmed || false
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      return Promise.reject(`OpenCode API error: ${response.status} - ${errorText}`);
    }

    const result = await response.json();

    // 3. Update session based on result
    if (result.workflow && result.workflow.nodes && result.workflow.edges) {
      await updateWorkflowNodes(sessionId, {
        nodes: result.workflow.nodes,
        edges: result.workflow.edges
      });
    }

    // 4. Add assistant message (if any)
    if (result.message) {
      await addMessage(sessionId, {
        role: 'assistant',
        content: result.message
      });
    }

    return {
      sessionId: result.sessionId,
      status: result.status,
      message: result.message,
      workflow: result.workflow,
      nextQuestion: result.nextQuestion
    };
  } catch (error) {
    return Promise.reject(`Failed to confirm workflow: ${error}`);
  }
}

export default NextAPI(handler);
