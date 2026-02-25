import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import handler from '../src/pages/api/core/workflow/ai/chat';
import { NextApiRequest, NextApiResponse } from 'next';
import { SseResponseEventEnum } from '@fastgpt/global/core/workflow/runtime/constants';
import { responseWrite } from '@fastgpt/service/common/response';

// Mocks
vi.mock('@fastgpt/service/support/permission/user/auth', () => ({
  authUserPer: vi
    .fn()
    .mockResolvedValue({ teamId: 'team1', tmbId: 'tmb1', userId: 'user1', isRoot: true })
}));

vi.mock('@fastgpt/service/core/workflow/ai/sessionController', () => ({
  createSession: vi.fn().mockResolvedValue({ _id: 'session1', sessionId: 'session1' }),
  getSession: vi.fn().mockResolvedValue({ _id: 'session1', sessionId: 'session1' }),
  addMessage: vi.fn().mockResolvedValue({}),
  updateWorkflowNodes: vi.fn(),
  setWorkflowValidation: vi.fn()
}));

vi.mock('@/service/core/workflow/ai/controller', () => ({
  getWorkflowTools: vi.fn().mockResolvedValue({
    tools: [],
    nodeTypes: [],
    categories: []
  })
}));

vi.mock('@fastgpt/service/common/response', () => ({
  jsonRes: vi.fn((res, { code, error }) => {
    console.log('jsonRes called:', { code, error });
    res.status(code || 500).json({ error });
  }),
  responseWrite: vi.fn((...args) => console.log('responseWrite called:', args))
}));

// Mock process.env
const originalEnv = process.env;

describe('AI Workflow Chat API', () => {
  beforeEach(() => {
    vi.resetModules();
    process.env = { ...originalEnv, OPENCODE_API_URL: 'https://mock-api.com' };
    global.fetch = vi.fn();
  });

  afterEach(() => {
    process.env = originalEnv;
    vi.restoreAllMocks();
  });

  it('should handle non-streaming request', async () => {
    const req = {
      body: {
        message: 'test message',
        sessionId: 'session1',
        stream: false
      },
      headers: {},
      socket: { remoteAddress: '127.0.0.1' }
    } as any;

    const res = {
      status: vi.fn().mockReturnThis(),
      json: vi.fn(),
      setHeader: vi.fn(),
      write: vi.fn(),
      end: vi.fn(),
      once: vi.fn(),
      on: vi.fn(),
      emit: vi.fn()
    } as any;

    const mockResponse = {
      sessionId: 'session1',
      message: 'Workflow generated',
      workflow: { nodes: [], edges: [] }
    };

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => mockResponse
    });

    await handler(req, res);

    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({
        sessionId: 'session1',
        message: 'Workflow generated',
        workflowPreview: {
          nodes: [],
          edges: []
        }
      })
    );
  });

  it('should handle streaming request and buffer correctly', async () => {
    const req = {
      body: {
        message: 'Generate a workflow for sentiment analysis',
        sessionId: 'session1',
        stream: true
      },
      headers: {},
      socket: { remoteAddress: '127.0.0.1' }
    } as any;

    const res = {
      setHeader: vi.fn(),
      write: vi.fn(),
      end: vi.fn(),
      status: vi.fn().mockReturnThis(),
      json: vi.fn(),
      once: vi.fn(),
      on: vi.fn(),
      emit: vi.fn()
    } as any;

    // Mock ReadableStream
    // Simulate a split response where the last chunk doesn't end with \n\n
    // Chunk 1: "event: message\ndata: part1\n\n" (complete)
    // Chunk 2: "event: message\ndata: part2" (incomplete, needs flush)
    const streamData = ['event: message\ndata: part1\n\n', 'event: message\ndata: part2'];
    const stream = new ReadableStream({
      start(controller) {
        const encoder = new TextEncoder();
        streamData.forEach((chunk) => controller.enqueue(encoder.encode(chunk)));
        controller.close();
      }
    });

    (global.fetch as any).mockResolvedValue({
      ok: true,
      body: stream
    });

    await handler(req, res);

    // Verify complete message was written
    expect(res.write).toHaveBeenCalledWith('event: message\ndata: part1\n\n');

    // Verify incomplete message was flushed (with appended \n\n)
    expect(res.write).toHaveBeenCalledWith('event: message\ndata: part2\n\n');

    expect(res.end).toHaveBeenCalled();
  });
});
