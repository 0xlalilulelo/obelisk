import { useAppStore } from '@/lib/store';

import { DiffViewer } from './DiffViewer';
import { TodayCard } from './TodayCard';

export function RightPane() {
  const pendingEdit = useAppStore((s) => s.pendingEdit);
  const activeBlockId = useAppStore((s) => s.activeBlockId);

  return (
    <aside className="min-h-0 overflow-y-auto border-l border-border-subtle bg-surface">
      {pendingEdit && activeBlockId ? (
        <DiffViewer blockId={activeBlockId} edit={pendingEdit} />
      ) : (
        <TodayCard blockId={activeBlockId} />
      )}
    </aside>
  );
}
