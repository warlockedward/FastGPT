import type { NextApiRequest, NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { TeamAppCreatePermissionVal } from '@fastgpt/global/support/permission/user/constant';
import { AppTypeEnum } from '@fastgpt/global/core/app/constants';
import { MongoApp } from '@fastgpt/service/core/app/schema';
import { getNanoid } from '@fastgpt/global/common/string/tools';
import type { ApiRequestProps } from '@fastgpt/service/type/next';
import { linkGeneratedWorkflow } from '@fastgpt/service/core/workflow/ai/sessionController';

async function handler(req: ApiRequestProps) {
  const body = req.body as {
    teamId: string;
    name: string;
    nodes?: any[];
    edges?: any[];
    folderId?: string;
    sessionId?: string;
  };

  const { teamId, tmbId, userId } = await authUserPer({
    req,
    authToken: true,
    per: TeamAppCreatePermissionVal
  });

  const { name, nodes = [], edges = [], folderId, sessionId } = body;

  const app = await MongoApp.create({
    teamId,
    tmbId,
    name,
    type: AppTypeEnum.workflow,
    modules: nodes,
    edges,
    parentId: folderId || null,
    avatar: '',
    intro: '',
    agentVersion: 'v2'
  });

  if (sessionId) {
    try {
      await linkGeneratedWorkflow(sessionId, String(app._id));
    } catch (error) {
      console.error('Failed to link generated workflow to session', error);
    }
  }

  return {
    workflowId: String(app._id),
    nodes,
    edges
  };
}

export default NextAPI(handler);
