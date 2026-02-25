import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import handler from '../src/pages/api/core/workflow/ai/plugin/validateCode';
import { authUserPer } from '@fastgpt/service/support/permission/user/auth';

// Mocks
vi.mock('@fastgpt/service/support/permission/user/auth', () => ({
  authUserPer: vi.fn()
}));

vi.mock('@fastgpt/service/common/response', () => ({
  jsonRes: vi.fn((res, { code, data, error }) => {
    res.status(code || 500).json(data || { error });
  })
}));

const originalEnv = process.env;

describe('Code Validation API', () => {
  beforeEach(() => {
    process.env = { ...originalEnv, SANDBOX_URL: 'http://mock-sandbox:3000' };
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

  it('should validate code successfully (JS)', async () => {
    const req = {
      body: {
        code: 'console.log("hello")',
        language: 'javascript',
        inputs: { foo: 'bar' }
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
        codeReturn: { result: 'success' },
        log: 'hello\n'
      })
    });

    await handler(req, res);

    expect(global.fetch).toHaveBeenCalledWith(
      'http://mock-sandbox:3000/sandbox/js',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          code: 'console.log("hello")',
          variables: { foo: 'bar' }
        })
      })
    );

    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({
        valid: true,
        output: 'hello\n\nResult: {"result":"success"}',
        executionTime: 0
      })
    );
  });

  it('should handle validation failure (Syntax Error from Sandbox)', async () => {
    const req = {
      body: {
        code: 'invalid code',
        language: 'javascript'
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
      ok: false,
      status: 500,
      text: async () => JSON.stringify({ message: 'SyntaxError: Unexpected token' })
    });

    await handler(req, res);

    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({
        valid: false,
        error: 'SyntaxError: Unexpected token'
      })
    );
  });

  it('should handle sandbox connection error (Network)', async () => {
    const req = {
      body: {
        code: 'test',
        language: 'javascript'
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

    (global.fetch as any).mockRejectedValue(new Error('Network error'));

    await handler(req, res);

    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({
        valid: false,
        error: 'Network error'
      })
    );
  });

  it('should fail if SANDBOX_URL is not configured', async () => {
    delete process.env.SANDBOX_URL;

    const req = {
      body: {
        code: 'test',
        language: 'javascript'
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
        error: 'SANDBOX_URL is not configured'
      })
    );
  });
});
