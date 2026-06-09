import {
  Archive,
  BarChart3,
  BookMarked,
  Calendar,
  Command,
  Dumbbell,
  LifeBuoy,
  type LucideIcon,
  MessagesSquare,
  Plus,
  Settings,
} from 'lucide-react';

import { useBlocks } from '@/lib/queries';
import { useAppStore } from '@/lib/store';
import { cn } from '@/lib/utils';

const NAV: { icon: LucideIcon; label: string }[] = [
  { icon: Dumbbell, label: 'Active Block' },
  { icon: MessagesSquare, label: 'Conversations' },
  { icon: BookMarked, label: 'Library' },
  { icon: BarChart3, label: 'Analytics' },
  { icon: Calendar, label: 'Schedule' },
  { icon: Settings, label: 'Settings' },
];

export function Sidebar() {
  const { data: blocks } = useBlocks();
  const activeBlockId = useAppStore((s) => s.activeBlockId);
  const setActiveBlock = useAppStore((s) => s.setActiveBlock);
  const setNewBlockOpen = useAppStore((s) => s.setNewBlockOpen);
  const setCommandPaletteOpen = useAppStore((s) => s.setCommandPaletteOpen);

  return (
    <aside className="flex min-h-0 flex-col border-r border-border-subtle bg-surface">
      <div className="px-4 py-4">
        <p className="label-caps">Performance</p>
        <p className="mt-1 text-body-base font-semibold text-primary-accent">Elite Tier</p>
      </div>

      <nav className="px-2">
        {NAV.map(({ icon: Icon, label }, i) => (
          <button
            key={label}
            className={cn(
              'flex w-full items-center gap-3 rounded px-3 py-2 text-body-base transition-colors',
              i === 0
                ? 'font-medium text-primary-accent'
                : 'text-foreground-muted hover:bg-surface-elevated hover:text-foreground',
            )}
          >
            <Icon className="h-4 w-4" strokeWidth={1.5} />
            {label}
          </button>
        ))}
      </nav>

      <div className="px-3 py-3">
        <button
          onClick={() => setNewBlockOpen(true)}
          className="flex w-full items-center justify-center gap-2 rounded border border-dashed border-border-subtle py-2.5 text-body-base text-foreground-muted hover:border-primary-accent/50 hover:text-foreground"
        >
          <Plus className="h-4 w-4" strokeWidth={1.5} />
          New Block
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2">
        {blocks && blocks.length > 0 ? (
          <ul className="space-y-0.5">
            {blocks.map((b) => (
              <li key={b.id}>
                <button
                  onClick={() => setActiveBlock(b.id)}
                  className={cn(
                    'flex w-full flex-col items-start rounded px-3 py-2 text-left transition-colors',
                    b.id === activeBlockId
                      ? 'bg-surface-elevated'
                      : 'hover:bg-surface-elevated/60',
                  )}
                >
                  <span className="truncate text-body-base font-medium">{b.name}</span>
                  <span className="truncate text-body-sm text-foreground-muted">
                    {b.program_model.replace('_', ' ')}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="px-3 py-6 text-body-sm text-foreground-muted">
            No Block yet — let&apos;s design one.
          </p>
        )}
      </div>

      <div className="border-t border-border-subtle p-2">
        <button
          onClick={() => setCommandPaletteOpen(true)}
          className="flex w-full items-center justify-between rounded border border-border-subtle px-3 py-2 text-body-sm text-foreground-muted hover:text-foreground"
        >
          <span className="flex items-center gap-2">
            <Command className="h-3.5 w-3.5" strokeWidth={1.5} />
            Command Palette
          </span>
          <span className="font-mono">⌘K</span>
        </button>
        <div className="mt-2 flex flex-col gap-1 px-1 text-body-sm text-foreground-muted">
          <span className="flex items-center gap-2">
            <LifeBuoy className="h-3.5 w-3.5" strokeWidth={1.5} /> Support
          </span>
          <span className="flex items-center gap-2">
            <Archive className="h-3.5 w-3.5" strokeWidth={1.5} /> Archive
          </span>
        </div>
      </div>
    </aside>
  );
}
