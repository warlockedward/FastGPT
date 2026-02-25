import type { NextApiRequest, NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { ReadPermissionVal } from '@fastgpt/global/support/permission/constant';
import { getWorkflowTools } from '@/service/core/workflow/ai/controller';

async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { teamId, isRoot } = await authUserPer({
    req,
    authToken: true,
    per: ReadPermissionVal
  });

  const result = await getWorkflowTools({ teamId, isRoot });

  return result;
}

export default NextAPI(handler);
