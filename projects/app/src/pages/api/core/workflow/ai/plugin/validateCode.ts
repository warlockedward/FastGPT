import type { NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { WritePermissionVal } from '@fastgpt/global/support/permission/constant';
import type { ApiRequestProps } from '@fastgpt/service/type/next';

const CodeValidationSchema = {
  type: 'object',
  properties: {
    code: { type: 'string' },
    language: { type: 'string', enum: ['python', 'javascript', 'typescript'] },
    inputs: { type: 'object' }
  },
  required: ['code', 'language']
};

async function handler(req: ApiRequestProps, res: NextApiResponse) {
  await authUserPer({
    req,
    authToken: true,
    per: WritePermissionVal
  });

  const body = req.body;
  const { code, language, inputs } = body;

  const opensandboxUrl = process.env.OPENSANDBOX_URL;
  if (!opensandboxUrl) {
    return Promise.reject('OPENSANDBOX_URL is not configured');
  }

  try {
    const response = await fetch(`${opensandboxUrl}/api/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code,
        language,
        inputs: inputs || {},
        timeout: 30000
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      return Promise.reject(`OpenSandbox error: ${response.status} - ${errorText}`);
    }

    const result = await response.json();

    return {
      valid: result.success || result.exitCode === 0,
      output: result.output || result.logs?.stdout || '',
      error: result.error || result.logs?.stderr || '',
      executionTime: result.executionTime || 0
    };
  } catch (error) {
    return Promise.reject(`Failed to validate code: ${error}`);
  }
}

export default NextAPI(handler);
