import { BarChart3 } from 'lucide-react';

/** Phase 1: placeholder. The analytics dashboard is out of scope until Phase 2. */
export function AnalyticsTab() {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center text-foreground-muted">
      <BarChart3 className="h-8 w-8" strokeWidth={1.25} />
      <p className="mt-3 text-body-base">Analytics arrive in Phase 2.</p>
      <p className="text-body-sm">Volume, intensity, and readiness trends.</p>
    </div>
  );
}
