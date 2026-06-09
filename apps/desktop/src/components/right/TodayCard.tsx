import type { CyclePlan } from '@obelisk/types';

import { useBlock } from '@/lib/queries';

const METRICS = [
  { label: 'Morning Bodyweight', value: '—' },
  { label: 'Sleep Quality', value: '—' },
  { label: 'HRV Readiness', value: '—' },
];

export function TodayCard({ blockId }: { blockId: string | null }) {
  const { data: block } = useBlock(blockId);
  const plan = block?.plan_json as CyclePlan | null | undefined;
  const today = plan?.day_template?.[0];

  return (
    <div className="flex flex-col gap-6 p-5">
      <section>
        <p className="label-caps mb-2">Today&apos;s session</p>
        {today ? (
          <div className="rounded-lg border border-border-subtle bg-background p-4">
            <p className="font-mono text-body-sm text-foreground-muted">{today.day}</p>
            <p className="mt-1 text-body-base font-semibold">{today.session}</p>
            <ul className="mt-3 space-y-1 text-body-sm text-foreground-muted">
              {today.blocks.slice(0, 5).map((b, i) => (
                <li key={i}>• {b.label}</li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="text-body-sm text-foreground-muted">No active session.</p>
        )}
      </section>

      <section>
        <p className="label-caps mb-2">Recent metrics</p>
        <div className="space-y-2">
          {METRICS.map((m) => (
            <div
              key={m.label}
              className="flex items-center justify-between rounded border border-border-subtle bg-background px-3 py-2"
            >
              <span className="text-body-sm text-foreground-muted">{m.label}</span>
              <span className="font-mono text-body-sm">{m.value}</span>
            </div>
          ))}
        </div>
        <p className="mt-2 text-body-sm text-foreground-muted/70">
          Wearable data lands in Phase 2.
        </p>
      </section>

      {plan && (
        <section>
          <p className="label-caps mb-2">Coach notes</p>
          <div className="rounded border border-border-subtle bg-background p-3 text-body-sm text-foreground-muted">
            {plan.nutrition.notes?.[0] ?? plan.subtitle ?? 'Stay consistent this week.'}
          </div>
        </section>
      )}
    </div>
  );
}
