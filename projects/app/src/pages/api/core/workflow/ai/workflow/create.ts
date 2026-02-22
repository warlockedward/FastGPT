import type { NextApiRequest, NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { TeamAppCreatePermissionVal } from '@fastgpt/global/support/permission/user/constant';
import { AppTypeEnum } from '@fastgpt/global/core/app/constants';
import { MongoApp } from '@fastgpt/service/core/app/schema';
import { getNanoid } from '@fastgpt/global/common/string/tools';
import type { ApiRequestProps } from '@fastgpt/service/type/next';

const CreateWorkflowSchema = {
  teamId: { type: 'string' },
  name: { type: 'string' },
  nodes: { type: 'array' },
  edges: { type: 'array' },
  folderId: { type: 'string' }
};

async function handler(req: ApiRequestProps) {
  const body = req.body as {
    teamId: string;
    name: string;
    nodes?: any[];
    edges?: any[];
    folderId?: string;
  };

  const { teamId, tmbId, userId } = await authUserPer({
    req,
    authToken: true,
    per: TeamAppCreatePermissionVal
  });

  const { name, nodes = [], edges = [], folderId } = body;

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

  return {
    workflowId: String(app._id),
    nodes,
    edges
  };
}

export default NextAPI(handler);
