import type { NextApiRequest, NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { ReadPermissionVal } from '@fastgpt/global/support/permission/constant';
import type {
  AiChatRequestType,
  AiChatResponseType
} from '@fastgpt/global/openapi/core/workflow/ai/api';
import { getSystemToolsWithInstalled } from '@fastgpt/service/core/app/tool/controller';

async function getWorkflowTools(req: NextApiRequest, teamId: string, isRoot: boolean) {
  const baseUrl = process.env.FASTGPT_API_URL || 'http://localhost:3000';
  try {
    const response = await fetch(`${baseUrl}/api/core/workflow/ai/nodes`, {
      headers: {
        Cookie: req.headers.cookie || ''
      }
    });
    if (!response.ok) {
      throw new Error('Failed to fetch nodes');
    }
    return await response.json();
  } catch (error) {
    const tools = await getSystemToolsWithInstalled({ teamId, isRoot });
    return {
      tools: tools.map((tool: any) => ({
        id: tool.id,
        name: tool.name,
        description: tool.description || tool.intro || '',
        flowNodeType: tool.flowNodeType,
        inputs: tool.inputs || [],
        outputs: tool.outputs || []
      })),
      nodeTypes: [],
      categories: []
    };
  }
}

async function handler(req: NextApiRequest, res: NextApiResponse): Promise<AiChatResponseType> {
  const { teamId, tmbId, userId, isRoot } = await authUserPer({
    req,
    authToken: true,
    per: ReadPermissionVal
  });

  const body = req.body as AiChatRequestType;
  const { message, sessionId, context } = body;

  const opencodeApiUrl = process.env.OPENCODE_API_URL;
  if (!opencodeApiUrl) {
    return Promise.reject('OPENCODE_API_URL is not configured');
  }

  const workflowData = await getWorkflowTools(req, teamId, isRoot);
  const { tools, nodeTypes, categories } = workflowData;

  const availablePlugins = tools
    .filter((tool: any) => tool.installed)
    .map((tool: any) => ({
      id: tool.id,
      name: tool.name,
      description: tool.description,
      flowNodeType: tool.flowNodeType,
      inputs: tool.inputs || [],
      outputs: tool.outputs || []
    }));

  const mode = context?.mode || 'create';
  const endpoint =
    mode === 'optimize' && context?.workflowId
      ? `${opencodeApiUrl}/api/ai-workflow/optimize`
      : `${opencodeApiUrl}/api/ai-workflow/generate`;

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.OPENCODE_API_KEY || ''}`
      },
      body: JSON.stringify({
        userIntent: message,
        sessionId,
        context: {
          existingWorkflow: context?.workflowId,
          availablePlugins: availablePlugins,
          nodeTypes: nodeTypes,
          categories: categories,
          enterpriseSystems: []
        },
        options: {
          generatePlugins: true,
          maxIterations: 3
        }
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      return Promise.reject(`OpenCode API error: ${response.status} - ${errorText}`);
    }

    const result = await response.json();

    return {
      sessionId: result.sessionId || sessionId || crypto.randomUUID(),
      message: result.message || '工作流已生成',
      suggestions: result.suggestions,
      workflowPreview: result.workflow
        ? {
            nodes: result.workflow.nodes,
            edges: result.workflow.edges
          }
        : undefined,
      status: result.status,
      questions: result.questions,
      validation_issues: result.validation_issues,
      low_confidence_mappings: result.low_confidence_mappings
    };
  } catch (error) {
    return Promise.reject(`Failed to connect to OpenCode API: ${error}`);
  }
}

export default NextAPI(handler);
