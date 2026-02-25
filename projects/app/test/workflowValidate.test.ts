import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import handler from '../src/pages/api/core/workflow/ai/workflow/validate';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';
import {
  getSession,
  setWorkflowValidation
} from '@fastgpt/service/core/workflow/ai/sessionController';

// Mocks
vi.mock('@fastgpt/service/support/permission/user/auth', () => ({
  authUserPer: vi.fn()
}));

vi.mock('@fastgpt/service/core/workflow/ai/sessionController', () => ({
  getSession: vi.fn(),
  setWorkflowValidation: vi.fn()
}));

vi.mock('@fastgpt/service/common/response', () => ({
  jsonRes: vi.fn((res, { code, data, error }) => {
    res.status(code || 500).json(data || { error });
  })
}));

const originalEnv = process.env;

describe('Workflow Validation API', () => {
  beforeEach(() => {
    process.env = { ...originalEnv, OPENCODE_API_URL: 'https://mock-opencode.com' };
    global.fetch = vi.fn();
    (authUserPer as any).mockResolvedValue({
      teamId: 'team1',
      tmbId: 'tmb1',
      userId: 'user1',
      isRoot: true
    });
  });

  afterEach(() => {
    process.env = originalEnv;
    vi.clearAllMocks();
  });

  it('should validate workflow successfully and update session', async () => {
    const req = {
      body: {
        workflow: { nodes: [], edges: [] },
        plugins: [],
        sessionId: 'session1'
      },
      headers: {},
      socket: { remoteAddress: '127.0.0.1' }
    } as any;

    const res = {
      status: vi.fn().mockReturnThis(),
      json: vi.fn(),
      setHeader: vi.fn(),
      getHeader: vi.fn(),
      write: vi.fn(),
      end: vi.fn(),
      once: vi.fn(),
      on: vi.fn(),
      emit: vi.fn()
    } as any;

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({
        valid: true,
        errors: [],
        suggestions: []
      })
    });

    (getSession as any).mockResolvedValue({
      _id: 'session1',
      sessionId: 'session1',
      teamId: 'team1'
    });

    await handler(req, res);

    expect(global.fetch).toHaveBeenCalledWith(
      'https://mock-opencode.com/api/ai-workflow/validate',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          workflow: { nodes: [], edges: [] },
          plugins: []
        })
      })
    );

    expect(getSession).toHaveBeenCalledWith('session1');
    expect(setWorkflowValidation).toHaveBeenCalledWith('session1', {
      isValid: true,
      validationErrors: []
    });

    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({
        valid: true,
        errors: [],
        suggestions: []
      })
    );
  });

  it('should handle validation failure from OpenCode API', async () => {
    const req = {
      body: {
        workflow: { nodes: [], edges: [] },
        plugins: []
      },
      headers: {},
      socket: { remoteAddress: '127.0.0.1' }
    } as any;

    const res = {
      status: vi.fn().mockReturnThis(),
      json: vi.fn(),
      setHeader: vi.fn(),
      getHeader: vi.fn(),
      write: vi.fn(),
      end: vi.fn(),
      once: vi.fn(),
      on: vi.fn(),
      emit: vi.fn()
    } as any;

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({
        valid: false,
        errors: ['Invalid node connection'],
        suggestions: []
      })
    });

    await handler(req, res);

    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({
        valid: false,
        errors: ['Invalid node connection']
      })
    );
  });

  it('should fail if OPENCODE_API_URL is not configured', async () => {
    delete process.env.OPENCODE_API_URL;

    const req = {
      body: {
        workflow: {},
        plugins: []
      },
      headers: {},
      socket: { remoteAddress: '127.0.0.1' }
    } as any;

    const res = {
      status: vi.fn().mockReturnThis(),
      json: vi.fn(),
      setHeader: vi.fn(),
      getHeader: vi.fn(),
      write: vi.fn(),
      end: vi.fn(),
      once: vi.fn(),
      on: vi.fn(),
      emit: vi.fn()
    } as any;

    await handler(req, res);

    expect(res.status).toHaveBeenCalledWith(500);
    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({
        error: 'OPENCODE_API_URL is not configured'
      })
    );
  });
});
