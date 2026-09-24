import type { ProviderStatus } from '../../../shared/types';
import type { ModelCompletionRequest, ModelCompletionResult, ModelProvider } from './types';

const DEMO_MODEL_NAME = 'demo-fast';
const DEMO_DEEP_MODEL_NAME = 'demo-deep-simulated';

/**
 * Honest demo provider: produces deterministic, clearly-labeled responses so
 * the full experience works end-to-end without an API key. It never claims to
 * be a real model — status and events all carry the "Demo Provider" label and
 * simulated: true.
 */
export class MockModelProvider implements ModelProvider {
  readonly id = 'mock' as const;
  readonly label = 'Demo Provider';

  status(): ProviderStatus {
    return {
      mode: 'mock',
      label: 'Demo Provider (no real model connected)',
      configured: true,
      configurationError: null,
      fastModel: DEMO_MODEL_NAME,
      deepModel: DEMO_DEEP_MODEL_NAME,
    };
  }

  async complete(request: ModelCompletionRequest): Promise<ModelCompletionResult> {
    const lastUser = [...request.messages].reverse().find((m) => m.role === 'user');
    const input = lastUser?.content ?? '';
    const text = this.composeResponse(input, request);
    return {
      text,
      provider: this.label,
      model: request.tier === 'deep' ? DEMO_DEEP_MODEL_NAME : DEMO_MODEL_NAME,
      simulated: true,
    };
  }

  private composeResponse(input: string, request: ModelCompletionRequest): string {
    const ctx = request.demoContext;
    const projectName = ctx?.projectName ?? null;
    const lower = input.toLowerCase();

    if (request.tier === 'deep') {
      return (
        `Here's my assessment (Demo Provider — simulated deep reasoning, not a real Claude response): ` +
        `the layered design — interface, router, providers, tools, and SQLite memory behind shared ` +
        `contracts — separates concerns cleanly, so scaling to multiple businesses is mostly a data and ` +
        `routing problem: add per-business project scoping, move approvals onto per-tenant policies, and ` +
        `swap the deterministic router for a model-based one behind the existing interface. The main real ` +
        `risks are memory retrieval quality and provider cost control, both isolated behind interfaces you ` +
        `can evolve. Configure a real Anthropic key to get an actual deep-reasoning answer.`
      );
    }

    if (lower.includes('what are we building') || lower.includes('building today')) {
      if (projectName && ctx?.projectSummary) {
        return (
          `We're building ${projectName}: ${ctx.projectSummary} ` +
          `(Demo Provider response — configure an Anthropic key for real model answers.)`
        );
      }
    }

    if (/(next\s+(three|3)\s+steps|break .* into)/.test(lower)) {
      return (
        `For ${projectName ?? 'the active project'}, I'd take these three steps next: ` +
        `1) finish the voice loop — push-to-talk, transcription, and spoken responses; ` +
        `2) wire the activity rail so every routing step is visible and honest; ` +
        `3) run the full demo flow, including the simulated mail approval and memory save. ` +
        `(Demo Provider response.)`
      );
    }

    const projectNote = projectName ? ` The active project is ${projectName}.` : '';
    return (
      `I received: "${truncate(input, 160)}".${projectNote} ` +
      `I'm running on the Demo Provider, so this is a simulated response — connect an Anthropic ` +
      `API key in .env to get real model answers.`
    );
  }
}

function truncate(text: string, max: number): string {
  return text.length <= max ? text : `${text.slice(0, max - 1)}…`;
}
