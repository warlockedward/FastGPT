import type { NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { WritePermissionVal } from '@fastgpt/global/support/permission/constant';
import type { ApiRequestProps } from '@fastgpt/service/type/next';
import {
  setWorkflowValidation,
  getSession
} from '@fastgpt/service/core/workflow/ai/sessionController';

async function handler(req: ApiRequestProps, res: NextApiResponse) {
  const { teamId } = await authUserPer({
    req,
    authToken: true,
    per: WritePermissionVal
  });

  const body = req.body;
  const { workflow, plugins, sessionId } = body;

  const opencodeApiUrl = process.env.OPENCODE_API_URL;
  if (!opencodeApiUrl) {
    return Promise.reject('OPENCODE_API_URL is not configured');
  }

  try {
    const response = await fetch(`${opencodeApiUrl}/api/ai-workflow/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.OPENCODE_API_KEY || ''}`
      },
      body: JSON.stringify({
        workflow,
        plugins: plugins || []
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      return Promise.reject(`OpenCode API error: ${response.status} - ${errorText}`);
    }

    const result = await response.json();

    // If sessionId is provided, update the validation status in the session
    if (sessionId) {
      const session = await getSession(sessionId);
      if (session && session.teamId === teamId) {
        await setWorkflowValidation(sessionId, {
          isValid: result.valid,
          validationErrors: result.errors || []
        });
      }
    }

    return {
      valid: result.valid,
      errors: result.errors || [],
      suggestions: result.suggestions || []
    };
  } catch (error) {
    return Promise.reject(`Failed to validate workflow: ${error}`);
  }
}

export default NextAPI(handler);
