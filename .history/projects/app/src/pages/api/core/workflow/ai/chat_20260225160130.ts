import type { NextApiRequest, NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { ReadPermissionVal } from '@fastgpt/global/support/permission/constant';
import type {
  AiChatRequestType,
  AiChatResponseType
} from '@fastgpt/global/openapi/core/workflow/ai/api';
import {
  createSession,
  addMessage,
  getSession,
  updateWorkflowNodes,
  setWorkflowValidation
} from '@fastgpt/service/core/workflow/ai/sessionController';
import { responseWrite } from '@fastgpt/service/common/response';
import { SseResponseEventEnum } from '@fastgpt/global/core/workflow/runtime/constants';
import { getWorkflowTools } from '@/service/core/workflow/ai/controller';

async function handler(req: NextApiRequest, res: NextApiResponse): Promise<any> {
  const { teamId, tmbId, userId, isRoot } = await authUserPer({
    req,
    authToken: true,
    per: ReadPermissionVal
  });

  const body = req.body as AiChatRequestType;
  const { message, sessionId, context, stream } = body;

  const opencodeApiUrl = process.env.OPENCODE_API_URL;
  if (!opencodeApiUrl) {
    return Promise.reject('OPENCODE_API_URL is not configured');
  }

  // Get or create session
  let currentSession = sessionId ? await getSession(sessionId) : null;
  if (!currentSession) {
    currentSession = await createSession({
      teamId,
      tmbId,
      mode: context?.mode || 'create'
    });
  }

  // Add user message to session
  const currentSessionId = currentSession.sessionId || currentSession._id.toString(); // Fallback if sessionId not in root
  await addMessage(currentSessionId, {
    role: 'user',
    content: message
  });

  const workflowData = await getWorkflowTools({ teamId, isRoot });
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

  // Streaming mode: forward to stream endpoint and pipe
  if (stream) {
    const endpoint = `${opencodeApiUrl}/api/ai-workflow/generate/stream`;

    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('X-Accel-Buffering', 'no');

    // Send sessionId immediately
    responseWrite({
      res,
      event: SseResponseEventEnum.aiWorkflowSession,
      data: JSON.stringify({ sessionId: currentSessionId })
    });

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${process.env.OPENCODE_API_KEY || ''}`
        },
        body: JSON.stringify({
          userIntent: message,
          sessionId: currentSessionId,
          context: {
            existingWorkflow: context?.workflowId,
            availablePlugins,
            nodeTypes,
            categories,
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
        responseWrite({
          res,
          event: SseResponseEventEnum.error,
          data: JSON.stringify({ message: `OpenCode API error: ${response.status}` })
        });
        res.end();
        return;
      }

      // Pipe the stream
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is empty');
      }
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.trim()) {
            res.write(line + '\n\n');
          }
        }
      }

      res.end();
    } catch (error) {
      responseWrite({
        res,
        event: SseResponseEventEnum.error,
        data: JSON.stringify({ message: String(error) })
      });
      res.end();
    }
    return;
  }

  // Non-streaming mode (backward compatible)
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
        sessionId: currentSessionId,
        context: {
          existingWorkflow: context?.workflowId,
          availablePlugins,
          nodeTypes,
          categories,
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
      sessionId: result.sessionId || currentSessionId || crypto.randomUUID(),
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
