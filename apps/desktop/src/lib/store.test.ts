import { beforeEach, describe, expect, it } from 'vitest';

import { useAppStore } from './store';

describe('useAppStore', () => {
  beforeEach(() => {
    useAppStore.setState({
      activeBlockId: null,
      activeTab: 'plan',
      newBlockOpen: false,
      commandPaletteOpen: false,
      pendingEdit: null,
    });
  });

  it('sets the active block and clears any pending edit', () => {
    useAppStore.getState().setPendingEdit({ editId: 'e1', diff: 'x' });
    useAppStore.getState().setActiveBlock('block-1');
    expect(useAppStore.getState().activeBlockId).toBe('block-1');
    expect(useAppStore.getState().pendingEdit).toBeNull();
  });

  it('switches the center tab', () => {
    useAppStore.getState().setActiveTab('coach');
    expect(useAppStore.getState().activeTab).toBe('coach');
  });

  it('toggles the new-block modal and command palette', () => {
    useAppStore.getState().setNewBlockOpen(true);
    useAppStore.getState().setCommandPaletteOpen(true);
    expect(useAppStore.getState().newBlockOpen).toBe(true);
    expect(useAppStore.getState().commandPaletteOpen).toBe(true);
  });
});
