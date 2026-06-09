export interface DiffRow {
  path: string;
  before: string;
  after: string;
}

/** Parse the backend's format_diff text into structured before/after rows. */
export function parseDiff(diff: string): DiffRow[] {
  const rows: DiffRow[] = [];
  const lines = diff.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(/^\s*•\s*(.+)$/);
    if (m) {
      const before = lines[i + 1]?.match(/was:\s*(.*)$/)?.[1] ?? '';
      const after = lines[i + 2]?.match(/will:\s*(.*)$/)?.[1] ?? '';
      rows.push({ path: m[1].trim(), before: before.trim(), after: after.trim() });
    }
  }
  return rows;
}

/** The human summary line from a format_diff block. */
export function diffSummary(diff: string): string {
  return diff.split('\n')[0]?.replace(/^PROPOSED CHANGES\s*—\s*/, '') ?? '';
}
