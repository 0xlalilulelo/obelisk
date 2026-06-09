/**
 * Typed Obelisk API client. Phase 1 is a thin hand-written fetch wrapper around
 * the /v1 surface plus an SSE reader for chat (ADR-006). A future task generates
 * the request/response layer from the OpenAPI spec; the shapes already live in
 * @obelisk/types so the swap is mechanical.
 */

import type {
  AthleteProfile,
  AthleteProfileInput,
  Block,
  BlockSummary,
  ChatMessage,
  ChatStreamEvent,
  CreateBlockInput,
  PlanResponse,
  SseDone,
  SsePlanEdit,
} from '@obelisk/types';

export interface ClientConfig {
  baseUrl: string;
  /** Returns the current Clerk session JWT (or null when signed out). */
  getToken: () => Promise<string | null>;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export function createClient({ baseUrl, getToken }: ClientConfig) {
  async function authHeaders(): Promise<Record<string, string>> {
    const token = await getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = {
      'Content-Type': 'application/json',
      ...(await authHeaders()),
      ...(init.headers ?? {}),
    };
    const resp = await fetch(`${baseUrl}${path}`, { ...init, headers });
    if (!resp.ok) {
      let detail = resp.statusText;
      try {
        const body = await resp.json();
        detail = (body as { detail?: string }).detail ?? detail;
      } catch {
        /* non-JSON error body */
      }
      throw new ApiError(resp.status, detail);
    }
    if (resp.status === 204) return undefined as T;
    return (await resp.json()) as T;
  }

  return {
    getProfile: () => request<AthleteProfile>('/v1/athlete/profile'),
    upsertProfile: (body: AthleteProfileInput) =>
      request<AthleteProfile>('/v1/athlete/profile', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    listBlocks: () => request<BlockSummary[]>('/v1/blocks'),
    getBlock: (id: string) => request<Block>(`/v1/blocks/${id}`),
    getPlan: (id: string) => request<PlanResponse>(`/v1/blocks/${id}/plan`),
    getMessages: (id: string, limit = 50, offset = 0) =>
      request<{ messages: ChatMessage[]; total: number; limit: number; offset: number }>(
        `/v1/blocks/${id}/messages?limit=${limit}&offset=${offset}`,
      ),
    createBlock: (body: CreateBlockInput) =>
      request<Block>('/v1/blocks', { method: 'POST', body: JSON.stringify(body) }),
    commitEdit: (blockId: string, editId: string) =>
      request<Block>(`/v1/blocks/${blockId}/edits/${editId}/commit`, { method: 'POST' }),
    rejectEdit: (blockId: string, editId: string) =>
      request<unknown>(`/v1/blocks/${blockId}/edits/${editId}/reject`, { method: 'POST' }),
    getArtifactUrl: (blockId: string, kind: string) =>
      request<{ kind: string; url: string; version: number }>(
        `/v1/blocks/${blockId}/artifact/${kind}`,
      ),

    /** Stream a chat turn over SSE, invoking onEvent for each parsed event. */
    async streamChat(
      blockId: string,
      message: string,
      onEvent: (event: ChatStreamEvent) => void,
      signal?: AbortSignal,
    ): Promise<void> {
      const headers = {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...(await authHeaders()),
      };
      const resp = await fetch(`${baseUrl}/v1/blocks/${blockId}/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ message }),
        signal,
      });
      if (!resp.ok || !resp.body) {
        throw new ApiError(resp.status, `chat stream failed (${resp.status})`);
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx: number;
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const frame = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const parsed = parseFrame(frame);
          if (parsed) onEvent(parsed);
        }
      }
    },
  };
}

export type ObeliskClient = ReturnType<typeof createClient>;

function parseFrame(frame: string): ChatStreamEvent | null {
  let event = 'message';
  const dataLines: string[] = [];
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
  }
  if (dataLines.length === 0) return null;
  const data = JSON.parse(dataLines.join('\n')) as Record<string, unknown>;
  switch (event) {
    case 'open':
      return { type: 'open', block_id: String(data.block_id) };
    case 'tool_use':
      return { type: 'tool_use', name: String(data.name) };
    case 'token':
      return { type: 'token', text: String(data.text) };
    case 'plan_edit':
      return { type: 'plan_edit', edit: data as unknown as SsePlanEdit };
    case 'done':
      return { type: 'done', done: data as unknown as SseDone };
    case 'error':
      return { type: 'error', message: String(data.message) };
    default:
      return null;
  }
}
