import { routeResultSchema, type RouteResult } from '../../shared/schemas/route';

export interface Router {
  route(requestId: string, input: string): RouteResult;
}

/**
 * Deterministic rule-based MVP router. Kept behind the Router interface so a
 * model-based router can replace it later. Every accepted request receives a
 * schema-validated route; empty input is rejected.
 */
export class RuleBasedRouter implements Router {
  route(requestId: string, input: string): RouteResult {
    const trimmed = input.trim();
    if (trimmed.length === 0) {
      throw new Error('Cannot route empty input');
    }
    const lower = trimmed.toLowerCase();

    let route: RouteResult;
    if (/^(please\s+|jarvis[,\s]+)*remember\b/.test(lower) || lower.includes('remember that')) {
      route = base(requestId, {
        intent: 'memory',
        specialist: 'memory',
        execution: 'memory_write',
        risk: 'none',
        requiresApproval: false,
        confidence: 0.95,
        reasonCode: 'explicit_memory_request',
      });
    } else if (
      /\b(draft|write|compose|send)\b.*\b(e-?mail|mail)\b/.test(lower) ||
      /\be-?mail\b.*\b(draft|to my|telling|saying)\b/.test(lower)
    ) {
      route = base(requestId, {
        intent: 'tool',
        specialist: 'mail',
        execution: 'mock_tool',
        risk: 'consequential',
        requiresApproval: true,
        confidence: 0.9,
        reasonCode: 'mail_draft_request',
      });
    } else if (
      /\b(evaluate|assess|architecture|scale|scalab|trade-?offs?|strateg|in-?depth|deep(ly)? analy|complex analysis|compare .* approaches)\b/.test(
        lower,
      )
    ) {
      route = base(requestId, {
        intent: 'deep_reasoning',
        specialist: 'general',
        execution: 'model',
        risk: 'none',
        requiresApproval: false,
        confidence: 0.75,
        reasonCode: 'deep_analysis_keywords',
      });
    } else if (
      /\b(project|build|plan|steps?|tasks?|roadmap|milestones?|deadline|prototype|what are we (building|working on))\b/.test(
        lower,
      )
    ) {
      route = base(requestId, {
        intent: 'project',
        specialist: 'project',
        execution: 'model',
        risk: 'none',
        requiresApproval: false,
        confidence: 0.8,
        reasonCode: 'project_planning_keywords',
      });
    } else {
      route = base(requestId, {
        intent: 'chat',
        specialist: 'general',
        execution: 'model',
        risk: 'none',
        requiresApproval: false,
        confidence: 0.5,
        reasonCode: 'general_chat_fallback',
      });
    }

    return routeResultSchema.parse(route);
  }
}

function base(
  requestId: string,
  rest: Omit<RouteResult, 'schemaVersion' | 'requestId'>,
): RouteResult {
  return { schemaVersion: 1, requestId, ...rest };
}
