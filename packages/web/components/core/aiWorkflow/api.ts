import { request } from '@fastgpt/web/common/api/request';

export const sendMessage = (data: {
  teamId: string;
  message: string;
  sessionId?: string;
  attachments?: string[];
  context?: {
    workflowId?: string;
    mode?: 'create' | 'optimize' | 'extend';
  };
}) => {
  return request.post('/core/workflow/ai/chat', data);
};

export const getAvailableNodes = (teamId: string) => {
  return request.get('/core/workflow/ai/nodes', {
    params: { teamId }
  });
};

export const createWorkflow = (data: {
  teamId: string;
  name: string;
  nodes: any[];
  edges: any[];
  folderId?: string;
}) => {
  return request.post('/core/workflow/ai/workflow/create', data);
};

export const listPlugins = (teamId: string) => {
  return request.get('/core/workflow/ai/plugin', {
    params: { teamId }
  });
};

export const createPlugin = (data: {
  teamId: string;
  name: string;
  description?: string;
  code: string;
}) => {
  return request.post('/core/workflow/ai/plugin', data);
};

export const updatePlugin = (
  pluginId: string,
  data: {
    name?: string;
    description?: string;
    code?: string;
  }
) => {
  return request.put(`/core/workflow/ai/plugin/${pluginId}`, data);
};

export const deletePlugin = (pluginId: string) => {
  return request.delete(`/core/workflow/ai/plugin/${pluginId}`);
};

export const confirmWorkflow = (data: {
  sessionId: string;
  answer?: string;
  confirmed?: boolean;
}) => {
  return request.post('/core/workflow/ai/workflow/confirm', data);
};

export const validateWorkflow = (data: {
  workflow: {
    nodes: any[];
    edges: any[];
  };
  plugins?: Array<{
    name: string;
    code: string;
  }>;
}) => {
  return request.post('/core/workflow/ai/workflow/validate', data);
};

export const mapVariables = (data: {
  workflow: {
    nodes: any[];
    edges: any[];
  };
}) => {
  return request.post('/api/ai-workflow/map-variables', data);
};

export const getWorkflowState = (sessionId: string) => {
  return request.get(`/api/ai-workflow/state/${sessionId}`);
};

export const confirmMappings = (
  sessionId: string,
  mappings: Array<{
    source_node_id: string;
    target_node_id: string;
  }>
) => {
  return request.post(`/api/ai-workflow/state/${sessionId}/confirm-mappings`, mappings);
};

export const recordFeedback = (data: {
  case_id?: string;
  was_modified: boolean;
  error_log?: string;
}) => {
  return request.post('/api/ai-workflow/feedback', data);
};
