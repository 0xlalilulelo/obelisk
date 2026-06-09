/** Shown when VITE_CLERK_PUBLISHABLE_KEY is missing — clearer than a Clerk crash. */
export function ConfigNotice() {
  return (
    <div className="flex h-full items-center justify-center bg-background p-8">
      <div className="max-w-md rounded-lg border border-border-subtle bg-surface p-6">
        <h1 className="text-headline-md font-semibold">Configuration needed</h1>
        <p className="mt-3 text-body-base text-foreground-muted">
          Set <code className="font-mono text-primary-accent">VITE_CLERK_PUBLISHABLE_KEY</code> (and{' '}
          <code className="font-mono text-primary-accent">VITE_API_BASE_URL</code>) in your{' '}
          <code className="font-mono">.env</code>, then restart the dev server.
        </p>
      </div>
    </div>
  );
}
