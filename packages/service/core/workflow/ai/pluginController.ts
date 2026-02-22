import { MongoAiPlugin } from './pluginSchema';

export const createPlugin = async (data: {
  teamId: string;
  name: string;
  description?: string;
  code: string;
}) => {
  const plugin = await MongoAiPlugin.create({
    ...data,
    status: 'draft'
  });
  return plugin;
};

export const updatePlugin = async (
  pluginId: string,
  data: {
    name?: string;
    description?: string;
    code?: string;
    status?: 'draft' | 'published' | 'archived';
  }
) => {
  const plugin = await MongoAiPlugin.findOneAndUpdate(
    { _id: pluginId },
    { $set: { ...data, updatedAt: new Date() } },
    { new: true }
  );
  return plugin;
};

export const getPlugin = async (pluginId: string) => {
  return MongoAiPlugin.findById(pluginId);
};

export const listPlugins = async (teamId: string) => {
  return MongoAiPlugin.find({ teamId }).sort({ updatedAt: -1 });
};

export const deletePlugin = async (pluginId: string) => {
  return MongoAiPlugin.findOneAndDelete({ _id: pluginId });
};

export const publishPlugin = async (pluginId: string) => {
  return MongoAiPlugin.findOneAndUpdate(
    { _id: pluginId },
    { $set: { status: 'published', updatedAt: new Date() } },
    { new: true }
  );
};
