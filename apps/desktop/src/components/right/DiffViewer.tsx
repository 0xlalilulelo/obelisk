import { Check, GitCompareArrows, Loader2, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { diffSummary, parseDiff } from '@/lib/diff';
import { useCommitEdit, useRejectEdit } from '@/lib/queries';
import { useAppStore, type PendingEdit } from '@/lib/store';

export function DiffViewer({ blockId, edit }: { blockId: string; edit: PendingEdit }) {
  const commit = useCommitEdit(blockId);
  const reject = useRejectEdit(blockId);
  const setPendingEdit = useAppStore((s) => s.setPendingEdit);

  const rows = parseDiff(edit.diff);
  const summary = diffSummary(edit.diff);
  const busy = commit.isPending || reject.isPending;

  async function onAccept() {
    await commit.mutateAsync(edit.editId);
    setPendingEdit(null);
  }
  async function onReject() {
    await reject.mutateAsync(edit.editId);
    setPendingEdit(null);
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-border-subtle px-5 py-4">
        <span className="h-2 w-2 rounded-full bg-copper" />
        <span className="label-caps">Proposed Change</span>
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-5">
        <div className="flex items-center gap-2 text-body-base text-foreground-muted">
          <GitCompareArrows className="h-4 w-4" strokeWidth={1.5} />
          {summary || 'Plan edit'}
        </div>

        {rows.length === 0 ? (
          <pre className="whitespace-pre-wrap rounded border border-border-subtle bg-background p-3 font-mono text-body-sm text-foreground-muted">
            {edit.diff}
          </pre>
        ) : (
          rows.map((r, i) => (
            <div key={i} className="space-y-1.5">
              <p className="font-mono text-body-sm text-foreground-muted">{r.path}</p>
              <div className="rounded border border-error/30 bg-error/5 px-3 py-2">
                <p className="label-caps text-error">Current</p>
                <p className="font-mono text-body-sm line-through">{r.before || '—'}</p>
              </div>
              <div className="rounded border border-primary-accent/40 bg-primary/10 px-3 py-2">
                <p className="label-caps text-primary-accent">Proposed</p>
                <p className="font-mono text-body-sm">{r.after || '—'}</p>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="space-y-2 border-t border-border-subtle p-4">
        <Button className="w-full" onClick={() => void onAccept()} disabled={busy}>
          {commit.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" strokeWidth={1.5} />}
          Accept Change
        </Button>
        <Button variant="secondary" className="w-full" onClick={() => void onReject()} disabled={busy}>
          <X className="h-4 w-4" strokeWidth={1.5} />
          Reject
        </Button>
      </div>
    </div>
  );
}
