import { z } from 'zod';

export const AiChatRequestSchema = z.object({
  teamId: z.string(),
  message: z.string(),
  sessionId: z.string().optional(),
  attachments: z.array(z.string()).optional(),
  context: z
    .object({
      workflowId: z.string().optional(),
      mode: z.enum(['create', 'optimize', 'extend']).optional()
    })
    .optional()
});

export type AiChatRequestType = z.infer<typeof AiChatRequestSchema>;

export const QuestionSchema = z.object({
  id: z.string(),
  question: z.string(),
  options: z.array(z.string()).optional()
});

export type QuestionType = z.infer<typeof QuestionSchema>;

export const AiChatResponseSchema = z.object({
  sessionId: z.string(),
  message: z.string(),
  suggestions: z.array(z.string()).optional(),
  workflowPreview: z
    .object({
      nodes: z.any(),
      edges: z.any()
    })
    .optional(),
  status: z.enum(['ready', 'need_more_info', 'failed', 'generating']).optional(),
  questions: z.array(QuestionSchema).optional()
});

export type AiChatResponseType = z.infer<typeof AiChatResponseSchema>;

export const WorkflowConfirmRequestSchema = z.object({
  sessionId: z.string(),
  answer: z.string().optional(),
  confirmed: z.boolean().optional()
});

export type WorkflowConfirmRequestType = z.infer<typeof WorkflowConfirmRequestSchema>;

export const WorkflowValidateRequestSchema = z.object({
  workflow: z.object({
    nodes: z.any(),
    edges: z.any()
  }),
  plugins: z
    .array(
      z.object({
        name: z.string(),
        code: z.string()
      })
    )
    .optional()
});

export type WorkflowValidateRequestType = z.infer<typeof WorkflowValidateRequestSchema>;

export const WorkflowValidateResponseSchema = z.object({
  valid: z.boolean(),
  errors: z.array(z.string()),
  suggestions: z.array(z.string()).optional()
});

export type WorkflowValidateResponseType = z.infer<typeof WorkflowValidateResponseSchema>;
