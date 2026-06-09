import type { ChatMessage } from '@obelisk/types';
import { ArrowUp, Loader2, Wrench } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { useApi } from '@/lib/api';
import { queryKeys, useMessages } from '@/lib/queries';
import { useAppStore } from '@/lib/store';
import { cn } from '@/lib/utils';
import { useQueryClient } from '@tanstack/react-query';

function extractText(content: unknown): string {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content
      .filter((b) => b && typeof b === 'object' && (b as { type?: string }).type === 'text')
      .map((b) => (b as { text?: string }).text ?? '')
      .join('\n')
      .trim();
  }
  return '';
}

/** A user-or-assistant message that has visible prose (hides tool-result frames). */
function isVisible(m: ChatMessage): boolean {
  if (m.role === 'tool') return false;
  if (m.role === 'user' && Array.isArray(m.content)) return false; // tool_result frame
  return extractText(m.content).length > 0;
}

export function CoachTab({ blockId }: { blockId: string }) {
  const api = useApi();
  const qc = useQueryClient();
  const { data: page } = useMessages(blockId);
  const setPendingEdit = useAppStore((s) => s.setPendingEdit);

  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [liveText, setLiveText] = useState('');
  const [pendingUser, setPendingUser] = useState<string | null>(null);
  const [tools, setTools] = useState<string[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  const history = (page?.messages ?? []).filter(isVisible);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [history.length, liveText, pendingUser]);

  async function send() {
    const text = input.trim();
    if (!text || streaming) return;
    setInput('');
    setPendingUser(text);
    setLiveText('');
    setTools([]);
    setStreaming(true);
    try {
      await api.streamChat(blockId, text, (event) => {
        if (event.type === 'token') setLiveText((t) => t + event.text);
        else if (event.type === 'tool_use') setTools((ts) => [...ts, event.name]);
        else if (event.type === 'plan_edit')
          setPendingEdit({ editId: event.edit.edit_id, diff: event.edit.diff });
        else if (event.type === 'error') setLiveText((t) => t + `\n[error: ${event.message}]`);
      });
    } finally {
      setStreaming(false);
      setPendingUser(null);
      setLiveText('');
      await qc.invalidateQueries({ queryKey: queryKeys.messages(blockId) });
      await qc.invalidateQueries({ queryKey: queryKeys.block(blockId) });
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="min-h-0 flex-1 space-y-4 overflow-y-auto p-6">
        {history.length === 0 && !pendingUser && (
          <p className="text-body-base text-foreground-muted">
            Ask the Block Coach anything — refine the plan, explain a decision, adapt a week.
          </p>
        )}
        {history.map((m) => (
          <Bubble key={m.id} role={m.role} text={extractText(m.content)} cost={m.cost_usd} />
        ))}
        {pendingUser && <Bubble role="user" text={pendingUser} />}
        {streaming && (
          <div className="space-y-2">
            {tools.map((t, i) => (
              <div key={i} className="flex items-center gap-2 text-body-sm text-foreground-muted">
                <Wrench className="h-3.5 w-3.5" strokeWidth={1.5} /> {t}
              </div>
            ))}
            <Bubble role="assistant" text={liveText || '…'} />
          </div>
        )}
      </div>

      <div className="shrink-0 border-t border-border-subtle p-4">
        <div className="flex items-end gap-2 rounded-lg border border-border-subtle bg-surface p-2 focus-within:border-primary-accent">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                void send();
              }
            }}
            rows={1}
            placeholder="Acknowledge or request adjustment…"
            className="max-h-32 flex-1 resize-none bg-transparent px-2 py-1.5 text-body-base focus:outline-none"
          />
          <button
            onClick={() => void send()}
            disabled={streaming || !input.trim()}
            className="flex h-8 w-8 items-center justify-center rounded bg-primary text-foreground disabled:opacity-40"
          >
            {streaming ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ArrowUp className="h-4 w-4" strokeWidth={2} />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

function Bubble({
  role,
  text,
  cost,
}: {
  role: string;
  text: string;
  cost?: number | null;
}) {
  const isUser = role === 'user';
  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[80%] whitespace-pre-wrap rounded-lg px-4 py-2.5 text-body-base',
          isUser
            ? 'bg-surface-elevated text-foreground'
            : 'border border-border-subtle bg-surface text-foreground',
        )}
      >
        {!isUser && <p className="label-caps mb-1 text-primary-accent">Obelisk</p>}
        {text}
        {typeof cost === 'number' && (
          <p className="mt-1.5 font-mono text-[10px] text-foreground-muted">
            ${cost.toFixed(4)}
          </p>
        )}
      </div>
    </div>
  );
}
