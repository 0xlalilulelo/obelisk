import { create } from 'zustand';

export type CenterTab = 'plan' | 'coach' | 'log' | 'analytics';

export interface PendingEdit {
  editId: string;
  diff: string;
}

interface AppState {
  activeBlockId: string | null;
  activeTab: CenterTab;
  newBlockOpen: boolean;
  commandPaletteOpen: boolean;
  /** When set, the right pane swaps from the Today card to the Diff viewer. */
  pendingEdit: PendingEdit | null;

  setActiveBlock: (id: string | null) => void;
  setActiveTab: (tab: CenterTab) => void;
  setNewBlockOpen: (open: boolean) => void;
  setCommandPaletteOpen: (open: boolean) => void;
  setPendingEdit: (edit: PendingEdit | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  activeBlockId: null,
  activeTab: 'plan',
  newBlockOpen: false,
  commandPaletteOpen: false,
  pendingEdit: null,

  setActiveBlock: (id) => set({ activeBlockId: id, pendingEdit: null }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setNewBlockOpen: (open) => set({ newBlockOpen: open }),
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
  setPendingEdit: (edit) => set({ pendingEdit: edit }),
}));
