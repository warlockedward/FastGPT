import { describe, it, expect, beforeAll } from 'vitest';

describe('AI Workflow API Tests', () => {
  const baseUrl = process.env.API_BASE_URL || 'http://localhost:3000';
  const teamId = 'test-team-id';

  describe('POST /api/core/workflow/ai/chat', () => {
    it('should send chat message and receive response', async () => {
      const response = await fetch(`${baseUrl}/api/core/workflow/ai/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          teamId,
          message: 'Create a simple workflow with chat node'
        })
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data).toHaveProperty('message');
      expect(data).toHaveProperty('sessionId');
    });

    it('should accept sessionId for conversation continuity', async () => {
      const sessionId = 'test-session-123';
      const response = await fetch(`${baseUrl}/api/core/workflow/ai/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          teamId,
          message: 'Add a condition node',
          sessionId
        })
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.sessionId).toBe(sessionId);
    });
  });

  describe('GET /api/core/workflow/ai/nodes', () => {
    it('should return available nodes', async () => {
      const response = await fetch(
        `${baseUrl}/api/core/workflow/ai/nodes?teamId=${teamId}`
      );

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data).toHaveProperty('nodes');
      expect(Array.isArray(data.nodes)).toBe(true);
    });
  });

  describe('POST /api/core/workflow/ai/workflow/create', () => {
    it('should create a new workflow', async () => {
      const response = await fetch(
        `${baseUrl}/api/core/workflow/ai/workflow/create`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            teamId,
            name: 'Test Workflow',
            nodes: [
              { id: 'start', flowNodeType: 'workflowStart' },
              { id: 'chat', flowNodeType: 'chatNode' }
            ],
            edges: [{ source: 'start', target: 'chat' }]
          })
        }
      );

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data).toHaveProperty('workflowId');
      expect(data).toHaveProperty('nodes');
      expect(data).toHaveProperty('edges');
    });
  });
});
