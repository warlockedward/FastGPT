import type { NextApiRequest, NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { WritePermissionVal } from '@fastgpt/global/support/permission/constant';
import { updatePlugin, deletePlugin, publishPlugin } from '@fastgpt/service/core/workflow/ai/pluginController';
import type { ApiRequestProps } from '@fastgpt/service/type/next';

async function handler(req: ApiRequestProps, res: NextApiResponse) {
  const { method } = req;
  const { pluginId } = req.query;

  if (!pluginId) {
    return { code: 'PLUGIN_ID_REQUIRED' };
  }

  await authUserPer({
    req,
    authToken: true,
    per: WritePermissionVal
  });

  switch (method) {
    case 'PUT': {
      const body = req.body as { name?: string; description?: string; code?: string };
      return await updatePlugin(pluginId as string, body);
    }
    case 'DELETE': {
      return await deletePlugin(pluginId as string);
    }
    case 'POST': {
      const { action } = req.body as { action?: string };
      if (action === 'publish') {
        return await publishPlugin(pluginId as string);
      }
      return { code: 'INVALID_ACTION' };
    }
    default:
      return { code: 'METHOD_NOT_ALLOWED' };
  }
}

export default NextAPI(handler);
