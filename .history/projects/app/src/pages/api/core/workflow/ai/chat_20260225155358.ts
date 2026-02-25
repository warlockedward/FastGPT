import type { NextApiRequest, NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { ReadPermissionVal } from '@fastgpt/global/support/permission/constant';
import type {
  AiChatRequestType,
  AiChatResponseType
} from '@fastgpt/global/openapi/core/workflow/ai/api';
import { getSystemToolsWithInstalled } from '@fastgpt/service/core/app/tool/controller';
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

async function handler(req: NextApiRequest, res: NextApiResponse): Promise<AiChatResponseType> {
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
  await addMessage(currentSession.sessionId, {
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
      data: JSON.stringify({ sessionId: currentSession.sessionId })
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
          sessionId: currentSession.sessionId,
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
      let fullResponseContent = '';

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

            // Try to parse event data to accumulate full response
            try {
              if (line.startsWith('data: ')) {
                const dataStr = line.slice(6);
                const data = JSON.parse(dataStr);
                // Accumulate content if it's a message chunk (this depends on the SSE format)
                // For now, we might not be able to reconstruct the full message easily from SSE without knowing the exact format
                // But we can try to capture the final event if available
              }
            } catch (e) {
              // ignore
            }
          }
        }
      }

      // Note: For streaming, we might need a separate mechanism to update the session
      // after the stream completes, or rely on the client to send a confirmation.
      // Or we can accumulate the response here if we know the structure.
      // Assuming the stream ends with a 'finish' event containing the full result?
      // Since we are just piping, we can't easily intercept without buffering everything.
      // For now, we'll leave the session update for streaming to a future improvement
      // or assume the OpenCode API handles state on its side (but we need local state).
      // A better approach might be to have the OpenCode API return the final state in the last event.

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
        sessionId,
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
