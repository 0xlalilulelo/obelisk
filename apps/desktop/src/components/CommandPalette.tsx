import { Search } from 'lucide-react';
import { useState } from 'react';

import { useAppStore } from '@/lib/store';

import { Dialog, DialogContent, DialogTitle } from './ui/dialog';

/** Phase 1 stub: ⌘K opens a search input. Real actions land in a later phase. */
export function CommandPalette() {
  const open = useAppStore((s) => s.commandPaletteOpen);
  const setOpen = useAppStore((s) => s.setCommandPaletteOpen);
  const [query, setQuery] = useState('');

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="top-[20%] translate-y-0 p-0">
        <DialogTitle className="sr-only">Command Palette</DialogTitle>
        <div className="flex items-center gap-3 border-b border-border-subtle px-4 py-3">
          <Search className="h-4 w-4 text-foreground-muted" strokeWidth={1.5} />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search commands…"
            className="flex-1 bg-transparent text-body-base focus:outline-none"
          />
          <span className="font-mono text-body-sm text-foreground-muted">⌘K</span>
        </div>
        <div className="px-4 py-6 text-center text-body-sm text-foreground-muted">
          Command actions arrive in a later phase.
        </div>
      </DialogContent>
    </Dialog>
  );
}
