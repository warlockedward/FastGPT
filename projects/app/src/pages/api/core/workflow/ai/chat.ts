import type { NextApiRequest, NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { ReadPermissionVal } from '@fastgpt/global/support/permission/constant';
import type { AiChatRequestType, AiChatResponseType } from '@fastgpt/global/openapi/core/workflow/ai/api';

async function handler(
  req: NextApiRequest,
  res: NextApiResponse
): Promise<AiChatResponseType> {
  const { teamId, tmbId, userId } = await authUserPer({
    req,
    authToken: true,
    per: ReadPermissionVal
  });

  const body = req.body as AiChatRequestType;
  const { message, sessionId, attachments, context } = body;

  const opencodeAgentUrl = process.env.OPENCODE_AGENT_URL;
  if (!opencodeAgentUrl) {
    return Promise.reject('OPENCODE_AGENT_URL is not configured');
  }

  try {
    const response = await fetch(`${opencodeAgentUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        team_id: teamId,
        message,
        session_id: sessionId,
        attachments,
        context
      })
    });

    if (!response.ok) {
      return Promise.reject(`OpenCode Agent error: ${response.status}`);
    }

    const result = await response.json();
    return result;
  } catch (error) {
    return Promise.reject(`Failed to connect to OpenCode Agent: ${error}`);
  }
}

export default NextAPI(handler);
