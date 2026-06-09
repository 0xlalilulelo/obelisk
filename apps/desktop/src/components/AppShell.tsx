import { useEffect } from 'react';

import { useBlocks } from '@/lib/queries';
import { useAppStore } from '@/lib/store';

import { CenterPane } from './center/CenterPane';
import { CommandPalette } from './CommandPalette';
import { NewBlockModal } from './NewBlockModal';
import { RightPane } from './right/RightPane';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

export function AppShell() {
  const { data: blocks } = useBlocks();
  const activeBlockId = useAppStore((s) => s.activeBlockId);
  const setActiveBlock = useAppStore((s) => s.setActiveBlock);
  const setCommandPaletteOpen = useAppStore((s) => s.setCommandPaletteOpen);

  // Default to the most recent Block once they load.
  useEffect(() => {
    if (!activeBlockId && blocks && blocks.length > 0) {
      setActiveBlock(blocks[0].id);
    }
  }, [activeBlockId, blocks, setActiveBlock]);

  // ⌘K / Ctrl+K opens the command palette.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(true);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [setCommandPaletteOpen]);

  return (
    <div className="flex h-full flex-col bg-background">
      <TopBar />
      <div className="grid min-h-0 flex-1 grid-cols-shell">
        <Sidebar />
        <CenterPane />
        <RightPane />
      </div>
      <NewBlockModal />
      <CommandPalette />
    </div>
  );
}
