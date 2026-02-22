import { z } from 'zod';

export const PluginCreateSchema = z.object({
  teamId: z.string(),
  name: z.string(),
  description: z.string().optional(),
  code: z.string()
});

export type PluginCreateType = z.infer<typeof PluginCreateSchema>;

export const PluginUpdateSchema = z.object({
  pluginId: z.string(),
  name: z.string().optional(),
  description: z.string().optional(),
  code: z.string().optional()
});

export type PluginUpdateType = z.infer<typeof PluginUpdateSchema>;

export const PluginRunSchema = z.object({
  pluginId: z.string(),
  input: z.record(z.string(), z.any()).optional()
});

export type PluginRunType = z.infer<typeof PluginRunSchema>;
