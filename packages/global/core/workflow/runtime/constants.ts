import { FlowNodeInputTypeEnum } from '../node/constant';

export enum SseResponseEventEnum {
  error = 'error',
  workflowDuration = 'workflowDuration',
  answer = 'answer',
  fastAnswer = 'fastAnswer',
  flowNodeStatus = 'flowNodeStatus',
  flowNodeResponse = 'flowNodeResponse',
  toolCall = 'toolCall',
  toolParams = 'toolParams',
  toolResponse = 'toolResponse',
  flowResponses = 'flowResponses',
  updateVariables = 'updateVariables',
  interactive = 'interactive',
  plan = 'plan',
  stepTitle = 'stepTitle',
  collectionForm = 'collectionForm',
  topAgentConfig = 'topAgentConfig',

  // AI Workflow streaming events
  aiWorkflowIntent = 'aiWorkflowIntent',
  aiWorkflowNodeGenerating = 'aiWorkflowNodeGenerating',
  aiWorkflowNodeGenerated = 'aiWorkflowNodeGenerated',
  aiWorkflowEdgeCreated = 'aiWorkflowEdgeCreated',
  aiWorkflowValidationStart = 'aiWorkflowValidationStart',
  aiWorkflowValidationProgress = 'aiWorkflowValidationProgress',
  aiWorkflowMappingProgress = 'aiWorkflowMappingProgress',
  aiWorkflowComplete = 'aiWorkflowComplete'
}

export enum DispatchNodeResponseKeyEnum {
  answerText = 'answerText',
  reasoningText = 'reasoningText',
  skipHandleId = 'skipHandleId',
  nodeResponse = 'responseData',
  nodeResponses = 'nodeResponses',
  nodeDispatchUsages = 'nodeDispatchUsages',
  childrenResponses = 'childrenResponses',
  toolResponses = 'toolResponses',
  assistantResponses = 'assistantResponses',
  rewriteHistories = 'rewriteHistories',
  interactive = 'INTERACTIVE',
  runTimes = 'runTimes',
  newVariables = 'newVariables',
  memories = 'system_memories',
  customFeedbacks = 'customFeedbacks'
}

export const needReplaceReferenceInputTypeList = [
  FlowNodeInputTypeEnum.reference,
  FlowNodeInputTypeEnum.settingDatasetQuotePrompt,
  FlowNodeInputTypeEnum.addInputParam,
  FlowNodeInputTypeEnum.custom
] as string[];

export const ConfirmPlanAgentText = 'CONFIRM';
