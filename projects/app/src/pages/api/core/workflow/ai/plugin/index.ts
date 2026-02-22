import type { NextApiRequest, NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { WritePermissionVal } from '@fastgpt/global/support/permission/constant';
import { createPlugin, listPlugins, getPlugin, updatePlugin, deletePlugin, publishPlugin } from '@fastgpt/service/core/workflow/ai/pluginController';
import type { ApiRequestProps } from '@fastgpt/service/type/next';

async function handler(req: ApiRequestProps, res: NextApiResponse) {
  const { method } = req;
  const { teamId } = await authUserPer({
    req,
    authToken: true,
    per: WritePermissionVal
  });

  switch (method) {
    case 'POST': {
      const body = req.body as { name: string; description?: string; code: string };
      const plugin = await createPlugin({ teamId, ...body });
      return plugin;
    }
    case 'GET': {
      const { pluginId } = req.query;
      if (pluginId) {
        return await getPlugin(pluginId as string);
      }
      return await listPlugins(teamId);
    }
    default:
      return { code: 'METHOD_NOT_ALLOWED' };
  }
}

export default NextAPI(handler);
