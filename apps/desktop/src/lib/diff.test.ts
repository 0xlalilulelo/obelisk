import { describe, expect, it } from 'vitest';

import { diffSummary, parseDiff } from './diff';

const SAMPLE = `PROPOSED CHANGES — 2 change(s) across: waves.
  • waves[0].days_override[2].blocks[0].label
      was:  Deadlift — main
      will: Trap Bar Deadlift — main
  • waves[0].training_maxes.trap_bar_deadlift
      was:  —
      will: 285

Approve these changes?`;

describe('parseDiff', () => {
  it('extracts before/after rows', () => {
    const rows = parseDiff(SAMPLE);
    expect(rows).toHaveLength(2);
    expect(rows[0].path).toBe('waves[0].days_override[2].blocks[0].label');
    expect(rows[0].before).toBe('Deadlift — main');
    expect(rows[0].after).toBe('Trap Bar Deadlift — main');
    expect(rows[1].after).toBe('285');
  });

  it('returns [] for a no-change diff', () => {
    expect(parseDiff('No changes to apply.')).toEqual([]);
  });
});

describe('diffSummary', () => {
  it('strips the PROPOSED CHANGES prefix', () => {
    expect(diffSummary(SAMPLE)).toBe('2 change(s) across: waves.');
  });
});
