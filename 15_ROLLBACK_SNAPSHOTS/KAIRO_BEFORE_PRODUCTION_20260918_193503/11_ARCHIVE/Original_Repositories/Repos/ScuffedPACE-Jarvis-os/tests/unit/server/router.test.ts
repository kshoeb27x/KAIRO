import { describe, expect, it } from 'vitest';
import { RuleBasedRouter } from '../../../src/server/orchestration/router';
import { routeResultSchema } from '../../../src/shared/schemas/route';

const router = new RuleBasedRouter();
const rid = () => crypto.randomUUID();

describe('RuleBasedRouter', () => {
  it('routes explicit memory requests to memory_write', () => {
    const route = router.route(
      rid(),
      'Remember that I prefer approval before any external action.',
    );
    expect(route.intent).toBe('memory');
    expect(route.execution).toBe('memory_write');
    expect(route.reasonCode).toBe('explicit_memory_request');
  });

  it('routes mail drafting to the mock mail tool with approval required', () => {
    const route = router.route(
      rid(),
      'Draft an email telling my collaborator the prototype will be ready tomorrow.',
    );
    expect(route.intent).toBe('tool');
    expect(route.specialist).toBe('mail');
    expect(route.execution).toBe('mock_tool');
    expect(route.risk).toBe('consequential');
    expect(route.requiresApproval).toBe(true);
  });

  it('routes architecture evaluation to deep reasoning', () => {
    const route = router.route(
      rid(),
      'Evaluate whether this architecture will scale to multiple businesses.',
    );
    expect(route.intent).toBe('deep_reasoning');
    expect(route.reasonCode).toBe('deep_analysis_keywords');
  });

  it('routes project planning requests to the project specialist', () => {
    expect(router.route(rid(), "Break tonight's build into the next three steps.").intent).toBe(
      'project',
    );
    expect(router.route(rid(), 'What are we building today?').intent).toBe('project');
  });

  it('falls back to chat for everything else', () => {
    const route = router.route(rid(), 'Good evening, how are you?');
    expect(route.intent).toBe('chat');
    expect(route.reasonCode).toBe('general_chat_fallback');
  });

  it('rejects empty input', () => {
    expect(() => router.route(rid(), '   ')).toThrow();
  });

  it('always produces a schema-valid route with confidence in range', () => {
    for (const input of ['hello', 'plan my day', 'draft an email to Sam', 'remember that x']) {
      const route = router.route(rid(), input);
      const parsed = routeResultSchema.parse(route);
      expect(parsed.confidence).toBeGreaterThanOrEqual(0);
      expect(parsed.confidence).toBeLessThanOrEqual(1);
      expect(parsed.schemaVersion).toBe(1);
    }
  });

  it('router schema rejects invalid routes', () => {
    expect(
      routeResultSchema.safeParse({
        schemaVersion: 2,
        requestId: 'not-a-uuid',
        intent: 'nonsense',
      }).success,
    ).toBe(false);
  });
});
