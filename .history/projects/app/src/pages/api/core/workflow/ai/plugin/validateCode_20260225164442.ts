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

  const sandboxUrl = process.env.SANDBOX_URL;
  if (!sandboxUrl) {
    return Promise.reject('SANDBOX_URL is not configured');
  }

  try {
    const endpoint = language === 'python' ? '/sandbox/python' : '/sandbox/js';
    const response = await fetch(`${sandboxUrl}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code,
        variables: inputs || {}
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      return Promise.reject(`Sandbox error: ${response.status} - ${errorText}`);
    }

    const result = await response.json();

    return {
      valid: true,
      output: result.log ? `${result.log}\nResult: ${JSON.stringify(result.codeReturn)}` : JSON.stringify(result.codeReturn),
      error: '',
      executionTime: 0 // Sandbox service currently doesn't return execution time
    };
  } catch (error) {
    return {
      valid: false,
      output: '',
      error: error instanceof Error ? error.message : String(error),
      executionTime: 0
    };
  }
}

export default NextAPI(handler);
