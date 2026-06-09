import type { Equipment, PrimaryModality } from '@obelisk/types';
import { useUser } from '@clerk/clerk-react';
import { Loader2 } from 'lucide-react';
import { useState } from 'react';

import { useCreateBlock, useProfile, useUpsertProfile } from '@/lib/queries';
import { useAppStore } from '@/lib/store';
import { cn } from '@/lib/utils';

import { Button } from './ui/button';
import { Dialog, DialogContent, DialogTitle } from './ui/dialog';

const MODALITIES: { value: PrimaryModality; label: string }[] = [
  { value: 'strength', label: 'Strength' },
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'endurance', label: 'Endurance' },
  { value: 'climbing', label: 'Climbing' },
  { value: 'tactical', label: 'Tactical' },
];

const EQUIPMENT: { value: Equipment; label: string }[] = [
  { value: 'bodyweight', label: 'Bodyweight' },
  { value: 'minimal', label: 'Minimal' },
  { value: 'home_gym', label: 'Home gym' },
  { value: 'full_gym', label: 'Full gym' },
];

// Barbell lifts the hybrid 5/3/1 builder programs. Providing 1RMs lets the coach
// route to a strength block instead of conservative novice linear progression.
const LIFTS: { key: string; label: string }[] = [
  { key: 'back_squat', label: 'Back Squat' },
  { key: 'bench_press', label: 'Bench Press' },
  { key: 'deadlift', label: 'Deadlift' },
  { key: 'strict_press', label: 'Strict Press' },
  { key: 'front_squat', label: 'Front Squat' },
  { key: 'power_clean', label: 'Power Clean' },
];

const STEPS = 6;

export function NewBlockModal() {
  const open = useAppStore((s) => s.newBlockOpen);
  const setOpen = useAppStore((s) => s.setNewBlockOpen);
  const setActiveBlock = useAppStore((s) => s.setActiveBlock);
  const setActiveTab = useAppStore((s) => s.setActiveTab);

  const { user } = useUser();
  const { data: existing } = useProfile();
  const upsertProfile = useUpsertProfile();
  const createBlock = useCreateBlock();

  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [goal, setGoal] = useState('');
  const [modality, setModality] = useState<PrimaryModality>('hybrid');
  const [equipment, setEquipment] = useState<Equipment>('full_gym');
  const [days, setDays] = useState(4);
  const [age, setAge] = useState('');
  const [bodyweight, setBodyweight] = useState('');
  const [oneRms, setOneRms] = useState<Record<string, string>>({});

  const busy = upsertProfile.isPending || createBlock.isPending;
  const error = upsertProfile.error || createBlock.error;

  function reset() {
    setStep(0);
    setName('');
    setGoal('');
    setModality('hybrid');
    setEquipment('full_gym');
    setDays(4);
    setAge('');
    setBodyweight('');
    setOneRms({});
  }

  // Entered 1RMs → a clean { lift_key: number } map, dropping blanks/invalid values.
  function collectOneRms(): Record<string, number> {
    const out: Record<string, number> = {};
    for (const [key, raw] of Object.entries(oneRms)) {
      const n = Number(raw);
      if (Number.isFinite(n) && n > 0) out[key] = Math.round(n);
    }
    return out;
  }

  async function finish() {
    const estimated1rm = { ...(existing?.estimated_1rm ?? {}), ...collectOneRms() };
    await upsertProfile.mutateAsync({
      name: existing?.name ?? user?.fullName ?? user?.firstName ?? 'Athlete',
      age: Number(age) || existing?.age || 30,
      bodyweight_lb: Number(bodyweight) || existing?.bodyweight_lb || null,
      sex: existing?.sex ?? null,
      height_in: existing?.height_in ?? null,
      resting_hr_bpm: existing?.resting_hr_bpm ?? null,
      estimated_1rm: estimated1rm,
      rep_max_known: existing?.rep_max_known ?? null,
      maf_data: existing?.maf_data ?? null,
      primary_goals: [goal],
      equipment,
      days_per_week: days,
      injuries: existing?.injuries ?? [],
      primary_modality: modality,
    });
    const block = await createBlock.mutateAsync({ name: name || goal.slice(0, 40), goal });
    setActiveBlock(block.id);
    setActiveTab('plan');
    setOpen(false);
    reset();
  }

  const canAdvance =
    (step === 0 && name.trim().length > 0) ||
    (step === 1 && goal.trim().length > 0) ||
    step === 2 ||
    step === 3 ||
    step === 4 ||
    step === 5;

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) reset();
      }}
    >
      <DialogContent>
        <DialogTitle className="text-headline-md font-semibold">Design a new Block</DialogTitle>

        {/* progress dots */}
        <div className="mt-3 flex gap-1.5">
          {Array.from({ length: STEPS }).map((_, i) => (
            <div
              key={i}
              className={cn('h-1.5 w-1.5 rounded-full', i <= step ? 'bg-primary-accent' : 'bg-border-subtle')}
            />
          ))}
        </div>

        <div className="mt-6 min-h-[180px]">
          {step === 0 && (
            <Field label="Name this Block" hint="A durable identifier, e.g. “Crucible-25”.">
              <input
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input"
                placeholder="Crucible-25"
              />
            </Field>
          )}
          {step === 1 && (
            <Field label="What's your primary goal?" hint="Plain language — the coach reads this.">
              <textarea
                autoFocus
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                rows={4}
                className="input resize-none"
                placeholder="12-week aerobic base + submaximal strength; bench priority"
              />
            </Field>
          )}
          {step === 2 && (
            <Field label="Primary modality">
              <Choices
                options={MODALITIES}
                value={modality}
                onChange={(v) => setModality(v as PrimaryModality)}
              />
            </Field>
          )}
          {step === 3 && (
            <Field label="Equipment & frequency">
              <Choices
                options={EQUIPMENT}
                value={equipment}
                onChange={(v) => setEquipment(v as Equipment)}
              />
              <div className="mt-4 flex items-center gap-3">
                <span className="text-body-base text-foreground-muted">Days / week</span>
                <input
                  type="number"
                  min={1}
                  max={7}
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  className="input w-20 font-mono"
                />
              </div>
            </Field>
          )}
          {step === 4 && (
            <Field label="About you" hint="Used to compute training maxes, MAF cap, and macros.">
              <div className="flex gap-4">
                <label className="flex-1">
                  <span className="label-caps">Age</span>
                  <input
                    type="number"
                    value={age}
                    onChange={(e) => setAge(e.target.value)}
                    className="input mt-1 font-mono"
                    placeholder="34"
                  />
                </label>
                <label className="flex-1">
                  <span className="label-caps">Bodyweight (lb)</span>
                  <input
                    type="number"
                    value={bodyweight}
                    onChange={(e) => setBodyweight(e.target.value)}
                    className="input mt-1 font-mono"
                    placeholder="175"
                  />
                </label>
              </div>
            </Field>
          )}
          {step === 5 && (
            <Field
              label="Tested lifts (optional)"
              hint="Your barbell 1RMs in lb. With these, the coach builds a 12-week 5/3/1 strength block; leave blank and it prescribes conservative linear progression instead."
            >
              <div className="grid grid-cols-2 gap-3">
                {LIFTS.map((lift) => (
                  <label key={lift.key}>
                    <span className="label-caps">{lift.label}</span>
                    <input
                      type="number"
                      min={0}
                      value={oneRms[lift.key] ?? ''}
                      onChange={(e) =>
                        setOneRms((m) => ({ ...m, [lift.key]: e.target.value }))
                      }
                      className="input mt-1 font-mono"
                      placeholder="—"
                    />
                  </label>
                ))}
              </div>
            </Field>
          )}
        </div>

        {error && (
          <p className="mt-2 text-body-sm text-error">{(error as Error).message}</p>
        )}

        <div className="mt-6 flex items-center justify-between">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0 || busy}
          >
            Back
          </Button>
          {step < STEPS - 1 ? (
            <Button size="sm" onClick={() => setStep((s) => s + 1)} disabled={!canAdvance}>
              Continue
            </Button>
          ) : (
            <Button size="sm" onClick={finish} disabled={busy}>
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}
              {busy ? 'Designing…' : 'Create Block'}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="text-body-base font-medium">{label}</h3>
      {hint && <p className="mt-1 text-body-sm text-foreground-muted">{hint}</p>}
      <div className="mt-3">{children}</div>
    </div>
  );
}

function Choices({
  options,
  value,
  onChange,
}: {
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {options.map((o) => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            'rounded border px-3 py-2.5 text-left font-mono text-body-base transition-colors',
            value === o.value
              ? 'border-primary-accent bg-surface-elevated text-foreground'
              : 'border-border-subtle text-foreground-muted hover:bg-surface-elevated',
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
