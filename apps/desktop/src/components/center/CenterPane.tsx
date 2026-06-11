import { Database } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { useAppStore, type CenterTab } from '@/lib/store';
import { cn } from '@/lib/utils';

import { AnalyticsTab } from './AnalyticsTab';
import { CoachTab } from './CoachTab';
import { LogTab } from './LogTab';
import { PlanTab } from './PlanTab';
import { SettingsTab } from './SettingsTab';

const TABS: { id: CenterTab; label: string }[] = [
  { id: 'plan', label: 'Plan' },
  { id: 'coach', label: 'Coach' },
  { id: 'log', label: 'Log' },
  { id: 'analytics', label: 'Analytics' },
];

export function CenterPane() {
  const activeBlockId = useAppStore((s) => s.activeBlockId);
  const activeTab = useAppStore((s) => s.activeTab);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const setNewBlockOpen = useAppStore((s) => s.setNewBlockOpen);

  // Settings is account-scoped, not Block-scoped — reachable with no active Block.
  if (activeTab === 'settings') {
    return (
      <main className="min-h-0 overflow-y-auto bg-background">
        <SettingsTab />
      </main>
    );
  }

  if (!activeBlockId) {
    return (
      <main className="flex min-h-0 items-center justify-center bg-background">
        <div className="flex w-[420px] flex-col items-center rounded-lg border border-border-subtle bg-surface px-10 py-12 text-center">
          <p className="text-headline-md font-semibold">No Block yet.</p>
          <p className="mt-1 text-body-base text-foreground-muted">Let&apos;s design one.</p>
          <Button className="mt-6" onClick={() => setNewBlockOpen(true)}>
            + New Block
          </Button>
          <div className="mt-8 flex items-center gap-2 border-t border-border-subtle pt-4 text-body-sm text-foreground-muted">
            <Database className="h-3.5 w-3.5" strokeWidth={1.5} />
            Awaiting primary input stream
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-0 flex-col bg-background">
      <div className="flex shrink-0 items-center gap-1 border-b border-border-subtle px-4">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={cn(
              'border-b-2 px-3 py-3 text-body-base transition-colors',
              activeTab === t.id
                ? 'border-primary-accent text-foreground'
                : 'border-transparent text-foreground-muted hover:text-foreground',
            )}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {activeTab === 'plan' && <PlanTab blockId={activeBlockId} />}
        {activeTab === 'coach' && <CoachTab blockId={activeBlockId} />}
        {activeTab === 'log' && <LogTab />}
        {activeTab === 'analytics' && <AnalyticsTab />}
      </div>
    </main>
  );
}
