import { UserButton } from '@clerk/clerk-react';

export function TopBar() {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border-subtle bg-surface px-4">
      <div className="flex items-center gap-2">
        <div className="flex h-6 w-6 items-center justify-center rounded border border-primary-accent/60">
          <div className="h-3 w-1 bg-primary-accent" />
        </div>
        <span className="text-body-base font-semibold tracking-tight">OBELISK</span>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 rounded border border-border-subtle px-3 py-1.5">
          <span className="label-caps">Readiness</span>
          {/* Stub until wearables land in Phase 2. */}
          <span className="font-mono text-body-sm text-foreground-muted">—</span>
        </div>
        <UserButton
          appearance={{ elements: { avatarBox: 'h-7 w-7 rounded' } }}
        />
      </div>
    </header>
  );
}
