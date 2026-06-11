import type { LiftPoint } from '@obelisk/types';
import { BarChart3 } from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { useLiftAnalytics } from '@/lib/queries';

/** The four main lifts charted in §2.7, with display names. */
const LIFTS: { key: string; label: string }[] = [
  { key: 'back_squat', label: 'Squat' },
  { key: 'bench_press', label: 'Bench' },
  { key: 'deadlift', label: 'Deadlift' },
  { key: 'strict_press', label: 'Press' },
];

export function AnalyticsTab() {
  const { data, isLoading, isError } = useLiftAnalytics();

  if (isLoading) {
    return <Centered>Loading e1RM history…</Centered>;
  }
  if (isError) {
    return <Centered>Couldn&apos;t load analytics.</Centered>;
  }

  const series = data?.series ?? {};
  const hasAny = LIFTS.some((l) => (series[l.key]?.length ?? 0) > 0);

  if (!hasAny) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-center text-foreground-muted">
        <BarChart3 className="h-8 w-8" strokeWidth={1.25} />
        <p className="mt-3 text-body-base">No estimated-1RM history yet.</p>
        <p className="text-body-sm">Log a few sets and your strength curves appear here.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-2">
      {LIFTS.map((lift) => (
        <LiftChart key={lift.key} label={lift.label} points={series[lift.key] ?? []} />
      ))}
    </div>
  );
}

function LiftChart({ label, points }: { label: string; points: LiftPoint[] }) {
  return (
    <div className="rounded-lg border border-border-subtle bg-surface p-4">
      <div className="mb-3 flex items-baseline justify-between">
        <span className="label-caps">{label}</span>
        {points.length > 0 && (
          <span className="font-mono text-body-sm text-foreground-muted">
            {points[points.length - 1].e1rm} lb
          </span>
        )}
      </div>
      <div className="h-40">
        {points.length === 0 ? (
          <div className="flex h-full items-center justify-center text-body-sm text-foreground-muted">
            No data yet
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid stroke="#26272B" strokeDasharray="2 4" vertical={false} />
              <XAxis
                dataKey="date"
                tick={{ fill: '#A1A1AA', fontSize: 10 }}
                tickFormatter={(d: string) => d.slice(5)}
                stroke="#26272B"
              />
              <YAxis
                tick={{ fill: '#A1A1AA', fontSize: 10 }}
                domain={['dataMin - 10', 'dataMax + 10']}
                stroke="#26272B"
                width={44}
              />
              <Tooltip
                contentStyle={{
                  background: '#1C1C1F',
                  border: '1px solid #26272B',
                  borderRadius: 4,
                  fontSize: 12,
                }}
                labelStyle={{ color: '#A1A1AA' }}
                itemStyle={{ color: '#F4F4F5' }}
                formatter={(v) => [`${v} lb`, 'e1RM']}
              />
              <Line
                type="monotone"
                dataKey="e1rm"
                stroke="#FFB784"
                strokeWidth={2}
                dot={{ r: 2, fill: '#FFB784' }}
                activeDot={{ r: 4 }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full items-center justify-center text-body-base text-foreground-muted">
      {children}
    </div>
  );
}
