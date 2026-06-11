import { useClerk, useUser } from '@clerk/clerk-react';
import { Activity, Heart, LogOut, Moon, Sun } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { useProfile } from '@/lib/queries';
import { useAppStore } from '@/lib/store';
import { cn } from '@/lib/utils';

export function SettingsTab() {
  const { user } = useUser();
  const { signOut } = useClerk();
  const { data: profile } = useProfile();
  const theme = useAppStore((s) => s.theme);
  const setTheme = useAppStore((s) => s.setTheme);

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6 p-6">
      <header>
        <h1 className="text-headline-md font-semibold">Settings</h1>
        <p className="text-body-sm text-foreground-muted">
          {user?.primaryEmailAddress?.emailAddress ?? 'Signed in'}
        </p>
      </header>

      {/* Profile */}
      <Section title="Profile">
        {profile ? (
          <dl className="grid grid-cols-2 gap-y-2 text-body-base">
            <Field label="Name" value={profile.name} />
            <Field label="Age" value={String(profile.age)} />
            <Field
              label="Bodyweight"
              value={profile.bodyweight_lb ? `${profile.bodyweight_lb} lb` : '—'}
            />
            <Field label="Days / week" value={String(profile.days_per_week)} />
            <Field label="Modality" value={profile.primary_modality} />
            <Field label="Goals" value={String(profile.primary_goals.length)} />
          </dl>
        ) : (
          <p className="text-body-sm text-foreground-muted">No profile yet.</p>
        )}
      </Section>

      {/* Appearance */}
      <Section title="Appearance">
        <div className="flex items-center justify-between">
          <span className="text-body-base">Theme</span>
          <div className="flex rounded border border-border-subtle p-0.5">
            <ThemeButton active={theme === 'dark'} onClick={() => setTheme('dark')} icon={Moon}>
              Dark
            </ThemeButton>
            <ThemeButton active={theme === 'light'} onClick={() => setTheme('light')} icon={Sun}>
              Light
            </ThemeButton>
          </div>
        </div>
      </Section>

      {/* Integrations */}
      <Section title="Integrations">
        <Integration
          icon={Heart}
          name="Apple Health"
          status="Synced on iOS"
          detail="Sleep, resting HR, and HRV feed your readiness."
        />
        <Integration
          icon={Activity}
          name="Strava"
          status="Coming soon"
          detail="Auto-import runs and rides."
          muted
        />
      </Section>

      {/* Notifications */}
      <Section title="Notifications">
        <NotifRow label="Morning session ping" on />
        <NotifRow label="Sunday weekly recap" on />
        <NotifRow label="Event alerts (PRs, deloads)" on />
        <p className="pt-1 text-body-sm text-foreground-muted">
          Delivery is managed on your iPhone; quiet hours 10pm–6am.
        </p>
      </Section>

      {/* Subscription */}
      <Section title="Plan">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-body-base font-medium">Free</p>
            <p className="text-body-sm text-foreground-muted">
              1 active Block, 20 chat messages / week.
            </p>
          </div>
          <Button variant="secondary" disabled>
            Upgrade to Plus
          </Button>
        </div>
        <p className="pt-2 text-body-sm text-foreground-muted">
          Billing via Stripe arrives with the subscription release.
        </p>
      </Section>

      {/* Account */}
      <Section title="Account">
        <Button variant="danger" onClick={() => signOut()}>
          <LogOut className="h-4 w-4" strokeWidth={1.5} />
          Sign out
        </Button>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-border-subtle bg-surface p-5">
      <h2 className="label-caps mb-4">{title}</h2>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-body-sm text-foreground-muted">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}

function ThemeButton({
  active,
  onClick,
  icon: Icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: typeof Moon;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-1.5 rounded px-3 py-1.5 text-body-sm transition-colors',
        active ? 'bg-surface-elevated text-foreground' : 'text-foreground-muted',
      )}
    >
      <Icon className="h-3.5 w-3.5" strokeWidth={1.5} />
      {children}
    </button>
  );
}

function Integration({
  icon: Icon,
  name,
  status,
  detail,
  muted,
}: {
  icon: typeof Heart;
  name: string;
  status: string;
  detail: string;
  muted?: boolean;
}) {
  return (
    <div className="flex items-start gap-3">
      <Icon
        className={cn('mt-0.5 h-4 w-4', muted ? 'text-foreground-muted' : 'text-primary-accent')}
        strokeWidth={1.5}
      />
      <div className="flex-1">
        <div className="flex items-center justify-between">
          <span className="text-body-base font-medium">{name}</span>
          <span className="text-body-sm text-foreground-muted">{status}</span>
        </div>
        <p className="text-body-sm text-foreground-muted">{detail}</p>
      </div>
    </div>
  );
}

function NotifRow({ label, on }: { label: string; on: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-body-base">{label}</span>
      <span
        className={cn(
          'rounded-full px-2 py-0.5 text-body-sm',
          on ? 'bg-primary-accent/15 text-primary-accent' : 'text-foreground-muted',
        )}
      >
        {on ? 'On' : 'Off'}
      </span>
    </div>
  );
}
