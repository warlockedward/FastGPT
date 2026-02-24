import type { NextApiRequest, NextApiResponse } from 'next';
import { NextAPI } from '@/service/middleware/entry';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import { getSystemToolsWithInstalled } from '@fastgpt/service/core/app/tool/controller';
import { getSystemTools } from '@fastgpt/service/core/app/tool/controller';
import { ReadPermissionVal } from '@fastgpt/global/support/permission/constant';
import { FlowNodeTypeEnum } from '@fastgpt/global/core/workflow/node/constant';

// Node type metadata for AI agent reference
const nodeTypeMetadata: Record<string, { label: string; category: string; description: string }> = {
  workflowStart: { label: '开始', category: 'core', description: '工作流入口节点' },
  chatNode: { label: 'AI 对话', category: 'ai', description: 'AI 对话节点，支持多种模型' },
  answerNode: { label: '直接回复', category: 'output', description: '直接返回内容给用户' },
  datasetSearchNode: { label: '知识库搜索', category: 'dataset', description: '从知识库检索相关内容' },
  datasetConcatNode: { label: '知识库拼接', category: 'dataset', description: '拼接多个知识库检索结果' },
  classifyQuestion: { label: '意图分类', category: 'ai', description: '根据用户输入分类意图' },
  contentExtract: { label: '内容提取', category: 'ai', description: '从文本中提取结构化数据' },
  httpRequest468: { label: 'HTTP 请求', category: 'integration', description: '发起 HTTP API 请求' },
  ifElseNode: { label: '条件分支', category: 'control', description: '根据条件执行不同分支' },
  agent: { label: 'AI Agent', category: 'ai', description: '具有规划能力的 AI Agent' },
  toolCall: { label: '工具调用', category: 'integration', description: '调用外部工具' },
  code: { label: '代码执行', category: 'tool', description: '执行自定义代码' },
  variableUpdate: { label: '变量更新', category: 'variable', description: '更新工作流变量' },
  globalVariable: { label: '全局变量', category: 'variable', description: '定义全局变量' },
  userSelect: { label: '用户选择', category: 'input', description: '让用户从选项中选择' },
  formInput: { label: '表单输入', category: 'input', description: '用户表单输入' },
  readFiles: { label: '读取文件', category: 'tool', description: '读取上传的文件' },
  loop: { label: '循环', category: 'control', description: '循环执行节点' },
  loopStart: { label: '循环开始', category: 'control', description: '循环开始节点' },
  loopEnd: { label: '循环结束', category: 'control', description: '循环结束节点' },
  pluginInput: { label: '插件输入', category: 'plugin', description: '插件输入参数' },
  pluginOutput: { label: '插件输出', category: 'plugin', description: '插件输出参数' },
  textEditor: { label: '文本编辑', category: 'tool', description: '富文本编辑器' },
  queryExtension: { label: '查询扩展', category: 'ai', description: '扩展用户查询' },
  tool: { label: '工具', category: 'integration', description: '调用已安装的工具' },
  toolSet: { label: '工具集', category: 'integration', description: '工具集合' },
  appModule: { label: '应用模块', category: 'integration', description: '调用其他应用' },
  pluginModule: { label: '插件模块', category: 'plugin', description: '调用插件' }
};

async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { teamId, isRoot } = await authUserPer({
    req,
    authToken: true,
    per: ReadPermissionVal
  });

  // Get installed tools
  const tools = await getSystemToolsWithInstalled({ teamId, isRoot });
  
  // Get all system tools (not just installed)
  const allTools = await getSystemTools();

  // Build node types list from FlowNodeTypeEnum
  const nodeTypes = Object.values(FlowNodeTypeEnum).map((type) => ({
    id: type,
    ...(nodeTypeMetadata[type] || { label: type, category: 'other', description: '' })
  }));

  return {
    // Installed tools with full details
    tools: tools.map((tool: any) => ({
      id: tool.id,
      pluginId: tool.pluginId,
      name: tool.name,
      description: tool.description || tool.intro || '',
      flowNodeType: tool.flowNodeType,
      installed: tool.installed,
      inputs: tool.inputs || [],
      outputs: tool.outputs || [],
      tags: tool.tags || [],
      version: tool.version,
      defaultInstalled: tool.defaultInstalled
    })),
    // All available node types in workflow
    nodeTypes,
    // Categories for reference
    categories: [
      { id: 'core', label: '核心节点' },
      { id: 'ai', label: 'AI 节点' },
      { id: 'input', label: '输入节点' },
      { id: 'output', label: '输出节点' },
      { id: 'control', label: '控制流' },
      { id: 'dataset', label: '知识库' },
      { id: 'integration', label: '集成' },
      { id: 'variable', label: '变量' },
      { id: 'tool', label: '工具' },
      { id: 'plugin', label: '插件' }
    ]
  };
}

export default NextAPI(handler);
