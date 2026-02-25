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
    process.env = { ...originalEnv, OPENSANDBOX_URL: 'https://mock-sandbox.com' };
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

  it('should validate code successfully', async () => {
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
      write: vi.fn(),
      end: vi.fn(),
      once: vi.fn(),
      on: vi.fn(),
      emit: vi.fn()
    } as any;

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({
        success: true,
        output: 'hello\n',
        executionTime: 100
      })
    });

    await handler(req, res);

    expect(global.fetch).toHaveBeenCalledWith(
      'https://mock-sandbox.com/api/validate',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          code: 'console.log("hello")',
          language: 'javascript',
          inputs: { foo: 'bar' },
          timeout: 30000
        })
      })
    );

    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({
        valid: true,
        output: 'hello\n',
        executionTime: 100
      })
    );
  });

  it('should handle validation failure', async () => {
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
      write: vi.fn(),
      end: vi.fn(),
      once: vi.fn(),
      on: vi.fn(),
      emit: vi.fn()
    } as any;

    (global.fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({
        success: false,
        error: 'SyntaxError',
        exitCode: 1
      })
    });

    await handler(req, res);

    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({
        valid: false,
        error: 'SyntaxError'
      })
    );
  });

  it('should handle sandbox connection error', async () => {
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
      write: vi.fn(),
      end: vi.fn()
    } as any;

    (global.fetch as any).mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => 'Internal Server Error'
    });

    await handler(req, res);

    // Expect error response handled by NextAPI wrapper or handler logic
    // The handler logic returns Promise.reject, which NextAPI should catch and send 500
    // But since we mock jsonRes, we expect it to be called with error

    // Check if jsonRes was called with 500
    expect(res.status).toHaveBeenCalledWith(500);
    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({
        error: expect.stringContaining('OpenSandbox error: 500')
      })
    );
  });

  it('should fail if OPENSANDBOX_URL is not configured', async () => {
    delete process.env.OPENSANDBOX_URL;

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
      write: vi.fn(),
      end: vi.fn()
    } as any;

    await handler(req, res);

    expect(res.status).toHaveBeenCalledWith(500);
    expect(res.json).toHaveBeenCalledWith(
      expect.objectContaining({
        error: 'OPENSANDBOX_URL is not configured'
      })
    );
  });
});
