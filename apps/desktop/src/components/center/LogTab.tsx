import { ClipboardList } from 'lucide-react';

/** Phase 1: empty state. The unified Log lands in Phase 2 (set logger, meals, etc.). */
export function LogTab() {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center text-foreground-muted">
      <ClipboardList className="h-8 w-8" strokeWidth={1.25} />
      <p className="mt-3 text-body-base">No entries yet.</p>
      <p className="text-body-sm">Sets, meals, mobility, and body metrics will appear here.</p>
    </div>
  );
}
