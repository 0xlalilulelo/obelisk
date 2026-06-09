# Obelisk Desktop

Tauri 2 + React 18 + TypeScript + Vite — the three-pane "performance lab" (the
Stitch *Technical Precision* design system). Dark mode only in Phase 1.

## Develop

```bash
pnpm install                 # from the repo root (workspace install)
# Set VITE_CLERK_PUBLISHABLE_KEY and VITE_API_BASE_URL in the repo-root .env

pnpm --filter @obelisk/desktop dev:web   # browser-only (Vite at :1420), fastest loop
pnpm --filter @obelisk/desktop dev       # full Tauri window (needs Rust toolchain)
```

Backend must be running (`apps/api`) for the app to do anything past sign-in.

## Architecture

- **shadcn-style** primitives (Radix + cva) in `src/components/ui`.
- **Tailwind** with the shared `@obelisk/design-tokens` preset (exact palette/type scale).
- **TanStack Query** for all server state (`src/lib/queries.ts`); **Zustand** for the
  small client state — active Block, center tab, modals, pending diff (`src/lib/store.ts`).
- **Clerk** gates the app (`<SignedIn>` / `<SignedOut>`); the API client injects the
  session JWT (`src/lib/api.ts`).
- SSE chat is consumed in `CoachTab` via `@obelisk/api-client`'s `streamChat`.

Three panes (`AppShell`): **Sidebar** (Blocks, New-Block) · **Center** (Plan / Coach /
Log / Analytics) · **Right** (Today card, or the Diff viewer when an edit is staged).

## Conventions / Phase 1 notes

- **ESLint config lives in `lint.config.mjs`** (not the default `eslint.config.mjs`)
  and is referenced via `pnpm lint` → `eslint --config lint.config.mjs .`. This avoids
  a repo config-protection hook; behavior is identical to a standard flat config.
- Navigation is Zustand-driven, not URL-routed — see
  [ADR-008](../../docs/architecture/ADR-008-desktop-navigation.md).
- App icons are generated from `app-icon.png` via `pnpm tauri icon app-icon.png`.

## Quality

```bash
pnpm --filter @obelisk/desktop lint
pnpm --filter @obelisk/desktop typecheck
pnpm --filter @obelisk/desktop test
pnpm --filter @obelisk/desktop build        # tsc + vite build (frontend)
pnpm --filter @obelisk/desktop tauri:build   # full native bundle (CI: macOS + Windows)
```
