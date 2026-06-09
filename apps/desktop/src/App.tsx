import { SignedIn, SignedOut, SignIn } from '@clerk/clerk-react';

import { AppShell } from './components/AppShell';

export default function App() {
  return (
    <>
      <SignedIn>
        <AppShell />
      </SignedIn>
      <SignedOut>
        <div className="flex h-full items-center justify-center bg-background">
          <div className="flex flex-col items-center gap-8">
            <div className="flex items-center gap-3">
              <ObeliskMark />
              <span className="text-headline-md font-semibold tracking-tight">OBELISK</span>
            </div>
            <SignIn
              appearance={{
                variables: {
                  colorBackground: '#141416',
                  colorPrimary: '#1F4E79',
                  colorText: '#F4F4F5',
                  colorInputBackground: '#0A0A0B',
                  borderRadius: '0.25rem',
                },
              }}
            />
          </div>
        </div>
      </SignedOut>
    </>
  );
}

function ObeliskMark() {
  return (
    <div className="flex h-7 w-7 items-center justify-center rounded border border-primary-accent/60">
      <div className="h-3.5 w-1.5 bg-primary-accent" />
    </div>
  );
}
