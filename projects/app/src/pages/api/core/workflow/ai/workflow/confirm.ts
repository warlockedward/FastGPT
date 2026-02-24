import type { NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { ReadPermissionVal } from '@fastgpt/global/support/permission/constant';
import type { ApiRequestProps } from '@fastgpt/service/type/next';

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

  const opencodeApiUrl = process.env.OPENCODE_API_URL;
  if (!opencodeApiUrl) {
    return Promise.reject('OPENCODE_API_URL is not configured');
  }

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
