import type { CyclePlan, TrainingDay } from '@obelisk/types';
import { Loader2 } from 'lucide-react';
import { useState } from 'react';

import { useBlock } from '@/lib/queries';
import { cn } from '@/lib/utils';

export function PlanTab({ blockId }: { blockId: string }) {
  const { data: block, isLoading } = useBlock(blockId);
  const [selectedDay, setSelectedDay] = useState(0);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-foreground-muted">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    );
  }
  const plan = block?.plan_json as CyclePlan | null | undefined;
  if (!plan) {
    return (
      <div className="p-8 text-body-base text-foreground-muted">
        This Block has no plan yet. Ask the Coach to draft one.
      </div>
    );
  }

  const days = plan.day_template ?? [];
  const totalWeeks = Math.max(plan.waves.length * 4, 1);
  const day = days[selectedDay];

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Block header + wave progress */}
      <section className="rounded-lg border border-border-subtle bg-surface p-5">
        <div className="flex items-baseline justify-between">
          <h2 className="text-headline-md font-semibold">{plan.title}</h2>
          <span className="font-mono text-body-sm text-foreground-muted">
            {totalWeeks} wks · {plan.program_model.replace('_', ' ')}
          </span>
        </div>
        <div className="mt-4 flex gap-2">
          {plan.waves.map((w, i) => (
            <div key={w.wave_num} className="flex-1">
              <div
                className={cn(
                  'h-1 rounded-full',
                  i === 0 ? 'bg-primary-accent' : 'bg-border-subtle',
                )}
              />
              <p className="mt-2 text-body-sm text-foreground-muted">
                Wave {w.wave_num}: {w.phase ?? 'strength'}{' '}
                <span className="font-mono">({w.week_range})</span>
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Week strip */}
      <section>
        <p className="label-caps mb-2">Week 1 — day template</p>
        <div className="flex gap-2 overflow-x-auto pb-1">
          {days.map((d, i) => (
            <button
              key={`${d.day}-${i}`}
              onClick={() => setSelectedDay(i)}
              className={cn(
                'min-w-[150px] shrink-0 rounded border p-3 text-left transition-colors',
                i === selectedDay
                  ? 'border-primary-accent bg-surface-elevated'
                  : 'border-border-subtle bg-surface hover:bg-surface-elevated/60',
              )}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-body-sm font-medium">{d.day}</span>
                <IntensityChip session={d.session} />
              </div>
              <p className="mt-2 truncate text-body-sm text-foreground-muted">{d.session}</p>
            </button>
          ))}
        </div>
      </section>

      {/* Day detail */}
      {day && <DayDetail day={day} />}

      {/* Nutrition footer */}
      <section className="flex items-center justify-between rounded border border-border-subtle bg-surface px-4 py-3">
        <span className="label-caps">Target nutrition</span>
        <div className="flex items-center gap-4 font-mono text-body-sm">
          <span>P {plan.nutrition.protein_g} g</span>
          <span>
            {plan.nutrition.calories_low.toLocaleString()}–
            {plan.nutrition.calories_high.toLocaleString()} kcal
          </span>
          <span className="text-foreground-muted">MAF {plan.maf_cap_bpm} bpm</span>
        </div>
      </section>
    </div>
  );
}

function DayDetail({ day }: { day: TrainingDay }) {
  const lifts = day.blocks.filter((b) => b.kind === 'main' || b.kind === 'accessory');
  const notes = day.blocks.filter((b) => b.kind === 'note');
  return (
    <section className="rounded-lg border border-border-subtle bg-surface p-5">
      <h3 className="text-body-base font-semibold">{day.session}</h3>
      <p className="mt-0.5 font-mono text-body-sm text-foreground-muted">{day.day}</p>

      {lifts.length > 0 && (
        <table className="mt-4 w-full text-body-base">
          <thead>
            <tr className="label-caps border-b border-border-subtle text-left">
              <th className="pb-2 font-semibold">Movement</th>
              <th className="pb-2 font-semibold">Type</th>
            </tr>
          </thead>
          <tbody className="font-mono">
            {lifts.map((b, i) => (
              <tr key={i} className="border-b border-border-subtle/50">
                <td className="py-2">{b.label}</td>
                <td className="py-2 text-foreground-muted">{b.kind}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {notes.length > 0 && (
        <ul className="mt-4 space-y-1 text-body-base text-foreground-muted">
          {notes.map((n, i) => (
            <li key={i}>• {n.note ?? n.label}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function IntensityChip({ session }: { session: string }) {
  const s = session.toLowerCase();
  const { label, cls } =
    /rest|recover/.test(s)
      ? { label: 'REST', cls: 'border-border-subtle text-foreground-muted' }
      : /heavy|strength|deadlift|squat|bench/.test(s)
        ? { label: 'HARD', cls: 'border-error/40 text-error' }
        : { label: 'MOD', cls: 'border-copper/40 text-copper' };
  return (
    <span className={cn('rounded-sm border px-1.5 py-0.5 text-[10px] font-semibold', cls)}>
      {label}
    </span>
  );
}
