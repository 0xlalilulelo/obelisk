# Phase 2 — Beta Handoff Checklist

**Goal:** a real human takes a TestFlight build of Obelisk to a closed beta of 5 concierge users.

**Scope:** Phase 2 feature code is complete and committed on `main` (`ce1cf19..00ac49d`). This document is the **credential + device handoff**, not new feature work. Every env var / Info.plist key below was read from the actual source on `main`; nothing here is invented.

> **Source-of-truth files** (read these if a key here is ever in doubt):
> backend `apps/api/src/obelisk_api/config.py` · iOS `apps/ios/Obelisk/AppConfig.swift` + `apps/ios/project.yml` · IAP `apps/ios/Obelisk.storekit` · desktop `apps/desktop/src/lib/config.ts` · CI `.github/workflows/{api,desktop,ios,e2e}.yml`.

---

## ⚠️ Read this first — five gotchas that will bite

| # | Gotcha | Why it matters | Action |
|---|--------|----------------|--------|
| 1 | **`DEV_AUTH_TOKEN` must be empty in prod, and `ENVIRONMENT=production`** | The dev-auth bypass in `auth/clerk.py` (`_dev_claims_or_none`) mints a synthetic user for any request bearing the token — but **only when `dev_auth_token` is set AND `environment != "production"`**. Either condition alone disables it; set both for defense in depth. | In prod env: `DEV_AUTH_TOKEN=` (empty) **and** `ENVIRONMENT=production`. |
| 2 | **`APPLE_STOREKIT_VERIFICATION=true` currently RAISES** | `services/apple.py` `decode_transaction()` throws `AppleVerificationUnavailableError` when verification is on — the x5c JWS chain check against Apple's root CA is **not wired** (the `app-store-server-library` integration is a TODO). The route turns that into `501 Not Implemented`. Decode-only (signature unverified) is **sandbox/dev/TestFlight only**, never trustworthy in production. | Keep `APPLE_STOREKIT_VERIFICATION=false` for the beta. Do **not** flip it on until the verifier is integrated (ADR-012). Beta runs against the sandbox, so decode-only is acceptable. |
| 3 | **`PUSH_SCHEDULER_ENABLED` must stay `false`** | ADR-014 + `services/scheduler.py` docstring: enabling requires durable per-athlete send-state columns (`last_morning_sent_at` / `last_opened_at`) so the one-per-day & defer-if-unopened rules survive restarts, **and** tz-correct local-time scheduling (the tick currently compares against UTC). Neither is done. | `PUSH_SCHEDULER_ENABLED=false`. Event-triggered / manual pushes still work; only the cron scheduler is gated off. |
| 4 | **Bundle id — RESOLVED to `fit.obelisk.ios`** | Previously inconsistent (`project.yml` had `app.obelisk.ios` vs `config.py`'s `fit.obelisk.ios`). Now reconciled in `project.yml` (`bundleIdPrefix: fit.obelisk` + all three target ids); `config.py` already defaulted to `fit.obelisk.ios`. | **You still must** create the App Store Connect app record and the two IAP products under `fit.obelisk.ios`, and set `APNS_TOPIC=fit.obelisk.ios`. The repo side is done. |
| 5 | **Never trust the client on billing** | Stripe state is authoritative **only** via the signature-verified `/v1/webhooks/stripe` handler (`stripe.Webhook.construct_event` with `STRIPE_WEBHOOK_SECRET`) — the Checkout redirect is not trusted. Apple receipts are verified **server-side** at `/v1/subscription/apple/verify`. | Ensure `STRIPE_WEBHOOK_SECRET` is set and the webhook endpoint is registered in the Stripe dashboard. Without the secret the webhook returns `503`. |

---

## 1. Accounts & credentials to provision

For each row: **what** to get, **where** to get it, and the **exact** env var / Info.plist key it lands in.

### Anthropic (the coach LLM)
- [ ] **API key** — dashboard: <https://console.anthropic.com> → API Keys → "Create Key" → `ANTHROPIC_API_KEY`
- [ ] (optional) override model via `OBELISK_MODEL` (default `claude-sonnet-4-6`) and per-session ceiling `MAX_COST_USD` (default `1.50`)

### Clerk (identity — backend verifies, clients sign in)
- [ ] **Issuer URL** — Clerk dashboard → API Keys / "Show JWT issuer" (e.g. `https://<slug>.clerk.accounts.dev`) → backend `CLERK_ISSUER`
- [ ] **Secret key** (`sk_live_…`) — Clerk dashboard → API Keys → backend `CLERK_SECRET_KEY`
- [ ] (optional) **Audience** → `CLERK_AUDIENCE` (leave unset to skip the `aud` check)
- [ ] **Publishable key** (`pk_live_…`) — Clerk dashboard → API Keys →
  - iOS Info.plist key **`CLERK_PUBLISHABLE_KEY`**
  - desktop env **`VITE_CLERK_PUBLISHABLE_KEY`**

### Managed Postgres (with `pgvector`)
- [ ] **Connection string** — provider (Neon / Supabase / RDS / Fly Postgres). Must support `pgvector` (CI uses `pgvector/pgvector:pg16`). → `DATABASE_URL` in the form `postgresql+psycopg://USER:PASS@HOST:5432/DB`
- [ ] Run `alembic upgrade head` against it before first traffic (see Backend section)

### S3 / R2 object storage (artifacts)
- [ ] **Bucket** — Cloudflare R2 or AWS S3 → `OBELISK_S3_BUCKET` (default `obelisk-artifacts`)
- [ ] **Region** → `OBELISK_S3_REGION` (R2 uses `auto`, the default)
- [ ] **Endpoint** (R2/S3-compatible only) → `OBELISK_S3_ENDPOINT` (omit for native AWS S3)
- [ ] **Access credentials** — set the standard AWS SDK env vars in the runtime (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`); these are read by boto, not by `config.py`.

### Sentry (error monitoring)
- [ ] **DSN** — Sentry → Project Settings → Client Keys (DSN) → `SENTRY_DSN`
  (When set, `main.py` inits Sentry with `environment=ENVIRONMENT`. Empty → Sentry off.)

### Stripe (desktop billing)
- [ ] **Secret key** (`sk_live_…`) — Stripe dashboard → Developers → API keys → `STRIPE_SECRET_KEY`
- [ ] **Webhook signing secret** (`whsec_…`) — Stripe → Developers → Webhooks → add endpoint `https://<api-host>/v1/webhooks/stripe`, subscribe to `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted` → `STRIPE_WEBHOOK_SECRET`
- [ ] **Monthly price id** (`price_…`) — Stripe → Products → Obelisk Plus monthly → `STRIPE_PRICE_MONTHLY`
- [ ] **Annual price id** (`price_…`) → `STRIPE_PRICE_ANNUAL`
- [ ] **Success / cancel URLs** — defaults `https://app.obelisk.fit/settings?checkout=success` / `…=cancel` → `STRIPE_SUCCESS_URL` / `STRIPE_CANCEL_URL` (override if the desktop deep-link host differs)

### Apple (IAP + receipt verification + APNs)
- [ ] **App Store Connect app record** — create the app with the chosen bundle id (gotcha #4). → drives `APPLE_BUNDLE_ID`
- [ ] **Two auto-renewable IAP products** in subscription group "Obelisk Plus":
  - [ ] `obelisk.plus.monthly` (P1M)
  - [ ] `obelisk.plus.annual` (P1Y)
  - Product ids must match `apps/ios/Obelisk.storekit` **exactly**.
- [ ] **App Store Server API key** (.p8 + Key ID + Issuer ID) — App Store Connect → Users and Access → Integrations → In-App Purchase keys. *Needed for the real x5c verifier when gotcha #2 is resolved; not consumed by an env var yet — keep it on file for the verifier integration.*
- [ ] **APNs Auth Key** (.p8) — Apple Developer → Certificates, Identifiers & Profiles → Keys → new key with **Apple Push Notifications service (APNs)** enabled. Capture:
  - Key ID → `APNS_KEY_ID`
  - Team ID (top-right of the developer portal) → `APNS_TEAM_ID`
  - the .p8 file **contents** (PEM text) → `APNS_PRIVATE_KEY`
  - Topic = the app bundle id → `APNS_TOPIC` (must equal the reconciled bundle id)
  - `APNS_USE_SANDBOX=true` for TestFlight/beta (default), `false` only for App Store production builds.

### PostHog (product analytics)
- [ ] **Project API key** (`phc_…`) — PostHog → Project Settings → `POSTHOG_API_KEY`
- [ ] **Host** — `https://us.i.posthog.com` (default) or EU/self-host → `POSTHOG_HOST`

---

## 2. Backend production config

### Env vars grouped by concern

**LLM**
- [ ] `ANTHROPIC_API_KEY`
- [ ] `OBELISK_MODEL` *(optional, default `claude-sonnet-4-6`)*
- [ ] `MAX_COST_USD` *(optional, default `1.50`)*

**Database**
- [ ] `DATABASE_URL`

**Auth (Clerk)**
- [ ] `CLERK_ISSUER`
- [ ] `CLERK_SECRET_KEY`
- [ ] `CLERK_AUDIENCE` *(optional)*
- [ ] `DEV_AUTH_TOKEN` → **empty** (gotcha #1)
- [ ] `DEV_AUTH_SUB` → leave default; irrelevant once the bypass is disabled

**Object storage**
- [ ] `OBELISK_S3_BUCKET` · `OBELISK_S3_REGION` · `OBELISK_S3_ENDPOINT` *(+ AWS creds in runtime)*

**Observability**
- [ ] `SENTRY_DSN`
- [ ] `ENVIRONMENT=production` ← **flag flip** (gotcha #1)

**Rate limiting**
- [ ] `RATE_LIMIT_ENABLED=true` (default; keep on for prod)

**Subscriptions**
- [ ] `STRIPE_SECRET_KEY` · `STRIPE_WEBHOOK_SECRET` · `STRIPE_PRICE_MONTHLY` · `STRIPE_PRICE_ANNUAL`
- [ ] `STRIPE_SUCCESS_URL` · `STRIPE_CANCEL_URL`
- [ ] `APPLE_BUNDLE_ID` (reconciled id, gotcha #4)
- [ ] `APPLE_STOREKIT_VERIFICATION=false` ← **flag flip / keep off** (gotcha #2)

**Push (APNs)**
- [ ] `APNS_KEY_ID` · `APNS_TEAM_ID` · `APNS_PRIVATE_KEY` · `APNS_TOPIC`
- [ ] `APNS_USE_SANDBOX=true` (TestFlight/beta)
- [ ] `PUSH_SCHEDULER_ENABLED=false` ← **flag flip / keep off** (gotcha #3)

**Analytics**
- [ ] `POSTHOG_API_KEY` · `POSTHOG_HOST`

**CORS**
- [ ] `CORS_ORIGINS` — defaults to the desktop dev-server + Tauri origins. Add the production desktop/web origin(s) if any.

### Production flag-flip summary
| Flag | Beta value | Reason |
|------|-----------|--------|
| `ENVIRONMENT` | `production` | disables dev-auth bypass; tags Sentry |
| `DEV_AUTH_TOKEN` | *(empty)* | disables dev-auth bypass |
| `APPLE_STOREKIT_VERIFICATION` | `false` | verifier not wired — `true` raises 501 |
| `PUSH_SCHEDULER_ENABLED` | `false` | ADR-014 prerequisites unmet |
| `APNS_USE_SANDBOX` | `true` | TestFlight uses the sandbox APNs env |
| `RATE_LIMIT_ENABLED` | `true` | keep abuse protection on |

### Deploy steps
- [ ] Build image: `docker build -f infra/Dockerfile -t obelisk-api .` (same Dockerfile CI builds)
- [ ] Inject all env vars (Doppler in shared envs per `config.py` docstring; nothing hardcoded)
- [ ] Run migrations: `alembic upgrade head` against prod `DATABASE_URL`
- [ ] Smoke `GET /healthz` (the only unauthenticated `/v1`-adjacent route)
- [ ] Confirm an authenticated request with a **real Clerk JWT** succeeds and a request with the old dev token is rejected (`401`)

---

## 3. iOS — signing, capabilities, StoreKit, TestFlight

**Bundle id:** reconcile to one value first (gotcha #4). The checklist below assumes the chosen id is set in `project.yml` `PRODUCT_BUNDLE_IDENTIFIER`, App Store Connect, and the backend `APPLE_BUNDLE_ID` / `APNS_TOPIC`.

**Regenerate the project:** `cd apps/ios && xcodegen generate` (the `.xcodeproj` is committed but generated from `project.yml`, ADR-013).

### Signing / provisioning
- [ ] Open `Obelisk.xcodeproj` in Xcode on the Mac
- [ ] Signing & Capabilities → select the team → automatic signing → flip `CODE_SIGNING_ALLOWED` back on for device (CI keeps it `NO` for unsigned simulator builds)
- [ ] Confirm `MARKETING_VERSION` (`0.1.0`) / `CURRENT_PROJECT_VERSION` (`1`) — bump build number per TestFlight upload

### Capabilities added in Xcode (NOT in `project.yml`)
Per ADR-013 these are omitted from `project.yml` so unsigned simulator/CI builds stay eligible; add them in **Signing & Capabilities** for device/TestFlight:
- [ ] **HealthKit** — entitlement `com.apple.developer.healthkit`. (The framework links via `project.yml`; the usage string `NSHealthShareUsageDescription` is already set. ADR-011: read-only, device→backend `POST /v1/wearable/healthkit`.)
- [ ] **HealthKit → Background Delivery** — entitlement `com.apple.developer.healthkit.background-delivery`. **Required** now that `HealthKitSync.startBackgroundDelivery()` registers observer queries for body weight + sleep; without it, background wake-ups won't fire (foreground sync still works).
- [ ] **Push Notifications** — adds the `aps-environment` entitlement (set to `development` for TestFlight sandbox, matching `APNS_USE_SANDBOX=true`)
- [ ] **Background Modes → Remote notifications** — so a content-available push can wake the app
- [ ] **In-App Purchase**

### Info.plist build settings (the keys the app actually reads — `AppConfig.swift`)
- [ ] **`OBELISK_API_URL`** = production API base URL (default falls back to `http://localhost:8000`)
- [ ] **`CLERK_PUBLISHABLE_KEY`** = Clerk `pk_live_…` (when present the app uses real Clerk sign-in; when absent it falls back to the dev token)
- [ ] **`OBELISK_DEV_TOKEN`** = **empty** for beta (dev escape hatch; must be empty so the app uses Clerk)
- [ ] **`OBELISK_DEV_BLOCK_ID`** = leave empty (dev-only Today fetch override)

### StoreKit config
- [ ] Confirm `Obelisk.storekit` product ids (`obelisk.plus.monthly`, `obelisk.plus.annual`) match the App Store Connect IAP products exactly (Section 1)
- [ ] For **TestFlight**, the app must purchase against **App Store Connect sandbox**, not the local `.storekit` file — ensure the scheme's StoreKit Configuration is unset (or not forced to the local file) for the TestFlight build

### TestFlight steps
- [ ] Archive (Product → Archive) a signed device build
- [ ] Upload via Xcode Organizer / `xcrun altool` to App Store Connect
- [ ] Complete export compliance + TestFlight test info
- [ ] Add the 5 beta testers (internal or external group); send invites
- [ ] Verify the build installs and launches on a real device before inviting users

---

## 4. Desktop build config

Desktop reads only `VITE_*` vars (Vite exposes nothing else to the client — `config.ts`).
- [ ] **`VITE_CLERK_PUBLISHABLE_KEY`** = Clerk `pk_live_…`
- [ ] **`VITE_API_BASE_URL`** = production API base URL (default `http://localhost:8000`)
- [ ] Build the Tauri bundle: `pnpm --filter @obelisk/desktop tauri:build` (CI builds it unsigned on macOS + Windows; sign for distribution)
- [ ] Code-sign / notarize for the OS you distribute to beta users (out of CI scope)
- [ ] Confirm Stripe checkout opens and the success/cancel URLs (`STRIPE_SUCCESS_URL`/`CANCEL_URL`) deep-link back correctly

---

## 5. CI — run all four workflows, confirm green

Trigger each on the real runners and confirm a green run before handoff.

| Workflow | Runner | What it does | Confidence |
|----------|--------|--------------|-----------|
| `api.yml` | ubuntu-latest | ruff · black --check · `mypy --strict` · pytest @ **90% coverage gate** · docker build | Known-good |
| `e2e.yml` | ubuntu-latest | real app + real Postgres (`pgvector/pgvector:pg16`), Clerk + Anthropic faked; `alembic upgrade head` then `e2e/smoke.py` | Known-good |
| `desktop.yml` | macos-latest + windows-latest | lint · typecheck · test · Tauri bundle (uses `pk_test_ci_placeholder`) | Known-good |
| `ios.yml` | **macos-15** | `brew install xcodegen` → `xcodegen generate` → `xcodebuild test` on a generic iOS Simulator, `CODE_SIGNING_ALLOWED=NO` | ⚠️ **rewritten, never run** |

- [ ] `api.yml` green on main
- [ ] `e2e.yml` green on main
- [ ] `desktop.yml` green on both macOS and Windows
- [ ] **`ios.yml` green** — ⚠️ this workflow was just rewritten to xcodegen-on-`macos-15` and has **not had a real CI run**. Expect to debug the runner's Xcode/simulator availability and the xcodegen install on first run. Treat the first run as a shakeout, not a guarantee.

---

## 6. Security pre-flight

- [ ] **`ENVIRONMENT=production` and `DEV_AUTH_TOKEN` empty** — dev-auth bypass disabled (gotcha #1); verify a request with the old dev token returns `401`
- [ ] **`OBELISK_DEV_TOKEN` empty in the iOS build** — app authenticates via Clerk, not the bypass
- [ ] **Stripe webhook signature verified** — `STRIPE_WEBHOOK_SECRET` set; `construct_event` rejects unsigned/forged payloads; missing secret yields `503` (never silent-trust)
- [ ] **Apple receipts verified server-side** — purchases flow through `POST /v1/subscription/apple/verify`; client tier claims are never trusted. (Beta = decode-only against sandbox; do not enable `APPLE_STOREKIT_VERIFICATION` until the x5c verifier is wired — gotcha #2.)
- [ ] **Rate limiting on** — `RATE_LIMIT_ENABLED=true`; per-athlete keying via `request.state.rate_limit_user`
- [ ] **CORS** restricted to known origins (`CORS_ORIGINS`); no wildcard added for prod
- [ ] **PHI-adjacent handling** (ADR-011) — HealthKit values never logged to stdout/Sentry, only counts; spot-check logs after first device sync
- [ ] **APNs device token treated as a credential** (ADR-014) — `/v1/notifications/register` stores it and never echoes it back
- [ ] **Secrets via Doppler / runtime injection**, none committed; confirm `.env` is not in the image
- [ ] **TLS** terminating in front of the API; `OBELISK_API_URL` / `VITE_API_BASE_URL` are `https://`

---

## 7. On-device verification (real iPhone + Apple Watch)

ADR-013 is explicit: hardware acceptance is **human-in-the-loop**. The build agent cannot exercise HealthKit-from-Watch, live StoreKit/APNs, or App Store Connect product config. Map the mission's 13-step acceptance flow to what is device-only:

### Acceptance flow — device-only checkpoints
- [ ] **Sign in** with a real Clerk account (not the dev token) → backend upserts the `User`
- [ ] **HealthKit permission prompt** appears and grants read access (gated by `authConfigured`)
- [ ] **Apple Watch data flows** — sleep, resting HR, HRV, active energy sync from a real Watch via `POST /v1/wearable/healthkit`; re-open the app and confirm dedup (no duplicates — idempotent on `sample_uuid`, ADR-011)
- [ ] **Readiness number** computes from real samples on Today
- [ ] **In-Session** — run a real session, log sets, confirm durability
- [ ] **Coach chat** streams a response (SSE)
- [ ] **IAP purchase** — buy Plus monthly *and* annual in the **sandbox**; confirm `/v1/subscription/apple/verify` flips the tier to `plus` and gated features unlock
- [ ] **Cross-platform unlock** — confirm the same account shows Plus on desktop (one `Subscription` row, ADR-012)
- [ ] **Cancellation** — one-tap deep-link to Manage Subscriptions; confirm tier reverts at `period_end`
- [ ] **Manual/event push** delivers to the device (sandbox APNs) once the device token is registered

### Device-gated features — now built, verify on device
These were wired after the initial handoff (simulator-compile verified; device behavior is what's left to confirm):
- [x] **APNs device registration on launch** — *built.* `AppDelegate` (`PushNotifications.swift`) registers for remote notifications, hex-encodes the token, and POSTs it via `NetworkClient.registerDevice`; the prompt is triggered from Today's onboarding, gated on `AppConfig.authConfigured`. **Verify on device:** permission prompt appears, token reaches `/v1/notifications/register`, a test push arrives.
- [x] **HealthKit background delivery** — *built.* `HealthKitSync.startBackgroundDelivery()` registers observer queries for body weight + sleep and calls `enableBackgroundDelivery(…, frequency: .daily)`, kicked off from `didFinishLaunchingWithOptions`. **Requires the background-delivery entitlement** (see §3). **Verify on device:** add a body-weight/sleep sample with the app backgrounded and confirm it syncs.

### Device-gated feature still to build
- [ ] **Dynamic Island Live Activity** — requires a **Widget Extension target** (no such target exists in `project.yml`; only `Obelisk` + test targets). Needs ActivityKit + the new target. This is the right piece to build with a device in the loop (its whole point is on-device Lock Screen / Dynamic Island rendering) rather than blind.

---

## 8. Recruit 5 concierge users

- [ ] Identify 5 athletes who match the target profile (hybrid strength + conditioning, own an Apple Watch)
- [ ] Collect their Apple IDs (emails) for the TestFlight external/internal group
- [ ] Send TestFlight invites; walk each through install + Clerk sign-in
- [ ] Provision sandbox tester Apple IDs if they need to exercise IAP without real charges
- [ ] Set up a direct feedback channel (shared thread / form) — concierge = high-touch, you respond personally
- [ ] Seed each user's first Block so Day 1 has a real session (avoids the empty-Today fallback)
- [ ] Define the beta success signal up front (e.g. ≥X sessions logged/week, readiness trusted, ≥1 purchase) and check in after week 1

---

### Done-when
All four CI workflows green (including the first real `ios.yml` run) · prod backend deployed with the six flag-flips correct · a signed TestFlight build installs on a real iPhone, syncs real Watch data, and completes a sandbox Plus purchase · 5 concierge users invited and onboarded.
