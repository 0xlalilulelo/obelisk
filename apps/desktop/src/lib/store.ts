import { create } from 'zustand';

export type CenterTab = 'plan' | 'coach' | 'log' | 'analytics' | 'settings';
export type Theme = 'dark' | 'light';

export interface PendingEdit {
  editId: string;
  diff: string;
}

const THEME_KEY = 'obelisk.theme';

function initialTheme(): Theme {
  try {
    return localStorage?.getItem(THEME_KEY) === 'light' ? 'light' : 'dark';
  } catch {
    return 'dark'; // non-browser env (tests) or storage disabled
  }
}

interface AppState {
  activeBlockId: string | null;
  activeTab: CenterTab;
  newBlockOpen: boolean;
  commandPaletteOpen: boolean;
  theme: Theme;
  /** When set, the right pane swaps from the Today card to the Diff viewer. */
  pendingEdit: PendingEdit | null;

  setActiveBlock: (id: string | null) => void;
  setActiveTab: (tab: CenterTab) => void;
  setNewBlockOpen: (open: boolean) => void;
  setCommandPaletteOpen: (open: boolean) => void;
  setPendingEdit: (edit: PendingEdit | null) => void;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  activeBlockId: null,
  activeTab: 'plan',
  newBlockOpen: false,
  commandPaletteOpen: false,
  theme: initialTheme(),
  pendingEdit: null,

  setActiveBlock: (id) => set({ activeBlockId: id, pendingEdit: null }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setNewBlockOpen: (open) => set({ newBlockOpen: open }),
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
  setPendingEdit: (edit) => set({ pendingEdit: edit }),
  setTheme: (theme) => {
    try {
      localStorage?.setItem(THEME_KEY, theme);
    } catch {
      /* storage unavailable — keep in-memory only */
    }
    set({ theme });
  },
  toggleTheme: () => get().setTheme(get().theme === 'dark' ? 'light' : 'dark'),
}));
