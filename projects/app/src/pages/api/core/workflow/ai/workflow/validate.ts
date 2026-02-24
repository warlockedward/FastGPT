import type { NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { WritePermissionVal } from '@fastgpt/global/support/permission/constant';
import type { ApiRequestProps } from '@fastgpt/service/type/next';

async function handler(req: ApiRequestProps, res: NextApiResponse) {
  await authUserPer({
    req,
    authToken: true,
    per: WritePermissionVal
  });

  const body = req.body;
  const { workflow, plugins } = body;

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
