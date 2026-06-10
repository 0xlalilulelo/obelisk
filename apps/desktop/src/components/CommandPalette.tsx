import { useClerk } from '@clerk/clerk-react';
import {
  BarChart3,
  Calendar,
  type LucideIcon,
  LogOut,
  MessagesSquare,
  Plus,
  ScrollText,
  Search,
  Settings,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { useAppStore } from '@/lib/store';
import { cn } from '@/lib/utils';

import { Dialog, DialogContent, DialogTitle } from './ui/dialog';

interface Command {
  id: string;
  label: string;
  group: string;
  icon: LucideIcon;
  run: () => void;
}

/** ⌘K command palette: Navigate, New Block, Open Settings, Sign Out (§2.7). */
export function CommandPalette() {
  const open = useAppStore((s) => s.commandPaletteOpen);
  const setOpen = useAppStore((s) => s.setCommandPaletteOpen);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const setNewBlockOpen = useAppStore((s) => s.setNewBlockOpen);
  const { signOut } = useClerk();

  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(0);

  const commands = useMemo<Command[]>(() => {
    const close = () => setOpen(false);
    const go = (tab: Parameters<typeof setActiveTab>[0]) => () => {
      setActiveTab(tab);
      close();
    };
    return [
      { id: 'nav-plan', label: 'Go to Plan', group: 'Navigate', icon: Calendar, run: go('plan') },
      { id: 'nav-coach', label: 'Go to Coach', group: 'Navigate', icon: MessagesSquare, run: go('coach') }, // prettier-ignore
      { id: 'nav-log', label: 'Go to Log', group: 'Navigate', icon: ScrollText, run: go('log') },
      { id: 'nav-analytics', label: 'Go to Analytics', group: 'Navigate', icon: BarChart3, run: go('analytics') }, // prettier-ignore
      { id: 'new-block', label: 'New Block', group: 'Actions', icon: Plus, run: () => { setNewBlockOpen(true); close(); } }, // prettier-ignore
      { id: 'settings', label: 'Open Settings', group: 'Actions', icon: Settings, run: go('settings') }, // prettier-ignore
      { id: 'sign-out', label: 'Sign Out', group: 'Account', icon: LogOut, run: () => { close(); void signOut(); } }, // prettier-ignore
    ];
  }, [setActiveTab, setNewBlockOpen, setOpen, signOut]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter((c) => c.label.toLowerCase().includes(q));
  }, [commands, query]);

  // Reset state whenever the palette opens or the result set changes.
  useEffect(() => {
    setSelected(0);
  }, [query, open]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelected((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelected((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      filtered[selected]?.run();
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) setQuery('');
      }}
    >
      <DialogContent className="top-[20%] translate-y-0 p-0">
        <DialogTitle className="sr-only">Command Palette</DialogTitle>
        <div className="flex items-center gap-3 border-b border-border-subtle px-4 py-3">
          <Search className="h-4 w-4 text-foreground-muted" strokeWidth={1.5} />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Search commands…"
            className="flex-1 bg-transparent text-body-base focus:outline-none"
          />
          <span className="font-mono text-body-sm text-foreground-muted">⌘K</span>
        </div>
        <div className="max-h-80 overflow-y-auto py-1">
          {filtered.length === 0 ? (
            <p className="px-4 py-6 text-center text-body-sm text-foreground-muted">
              No matching commands.
            </p>
          ) : (
            filtered.map((c, i) => (
              <button
                key={c.id}
                onMouseEnter={() => setSelected(i)}
                onClick={() => c.run()}
                className={cn(
                  'flex w-full items-center gap-3 px-4 py-2.5 text-left text-body-base',
                  i === selected ? 'bg-surface-elevated text-foreground' : 'text-foreground-muted',
                )}
              >
                <c.icon className="h-4 w-4" strokeWidth={1.5} />
                <span className="flex-1">{c.label}</span>
                <span className="text-body-sm text-foreground-muted/70">{c.group}</span>
              </button>
            ))
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
