import { z } from 'zod';

export const AiChatRequestSchema = z.object({
  teamId: z.string(),
  message: z.string(),
  sessionId: z.string().optional(),
  attachments: z.array(z.string()).optional(),
  context: z.object({
    workflowId: z.string().optional(),
    mode: z.enum(['create', 'optimize', 'extend']).optional()
  }).optional()
});

export type AiChatRequestType = z.infer<typeof AiChatRequestSchema>;

export const AiChatResponseSchema = z.object({
  sessionId: z.string(),
  message: z.string(),
  suggestions: z.array(z.string()).optional(),
  workflowPreview: z.object({
    nodes: z.any(),
    edges: z.any()
  }).optional()
});

export type AiChatResponseType = z.infer<typeof AiChatResponseSchema>;
