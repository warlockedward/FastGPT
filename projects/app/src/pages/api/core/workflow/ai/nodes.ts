import type { NextApiRequest, NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { getSystemToolsWithInstalled } from '@fastgpt/service/core/app/tool/controller';
import { ReadPermissionVal } from '@fastgpt/global/support/permission/constant';

async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { teamId, isRoot } = await authUserPer({
    req,
    authToken: true,
    per: ReadPermissionVal
  });

  const tools = await getSystemToolsWithInstalled({ teamId, isRoot });

  return {
    nodes: tools.map((tool: any) => ({
      id: tool.id,
      name: tool.name,
      flowNodeType: tool.flowNodeType,
      installed: tool.installed,
      intro: tool.intro
    }))
  };
}

export default NextAPI(handler);
