# Obelisk iOS

Swift + SwiftUI (iOS 17+). Built and simulator-verified on a local Mac (ADR-013,
which supersedes ADR-007's "no local Mac" premise).

## Project generation

The Xcode project is generated from [`project.yml`](project.yml) by
[XcodeGen](https://github.com/yonsson/XcodeGen) — `project.yml` is the source of
truth; `Obelisk.xcodeproj` is git-ignored and regenerated.

```bash
brew install xcodegen
cd apps/ios
xcodegen generate
open Obelisk.xcodeproj      # or build from the CLI:

# Build + test on a booted simulator (the SDK that ships with Xcode may be newer
# than the installed simulator runtimes; target a concrete booted device):
xcrun simctl boot "iPhone 17 Pro"
xcodebuild test -project Obelisk.xcodeproj -scheme Obelisk \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro'
```

Point the app at a backend with the `OBELISK_API_URL` / `OBELISK_DEV_TOKEN` /
`OBELISK_DEV_BLOCK_ID` Info.plist keys (see `AppConfig.swift`). With none set, the
Today screen falls back to a bundled sample session so the In-Session screen is
demonstrable without a server.

## What's built (Phase 2, first iOS milestone)

- **App shell:** 5-tab `TabView` (Today / Plan / Coach / Log / Profile), dark mode.
  Plan/Coach/Log/Profile are placeholders this milestone.
- **Today:** readiness composite with visible factors + behavioral guidance
  (`GET /v1/athlete/readiness`); today's session card; **Start Session**.
- **In-Session (the workhorse, PRD §2.1):** full-screen takeover, idle-timer
  disabled, large-mono hero with prior-session value, set rows with 56pt ± steppers,
  RPE chip, confirm checkbox, swipe-to-copy / swipe-to-delete, inline plate
  calculator (45/35 bar), auto-starting drift-free rest timer in a 0.4-detent sheet,
  haptics (set log / rest done / **copper PR pulse**), end-session RPE prompt.
- **Durability (ADR-009):** every confirmed set writes to a local SwiftData queue
  immediately, then a `SyncEngine` flushes to `POST /v1/log` — idempotent on a
  device UUID, so a gym-basement reconnect never double-logs.
- **Networking:** `NetworkClient` actor over `/v1`; Codable mirrors of the backend
  schemas.
- **Tests:** plate math, Epley e1RM (matches the backend), rest formatting, and
  client pre-fill — `xcodebuild test`, 9 passing.

## Next iOS milestones

Clerk sign-in + block selection, the Coach SSE chat, the Plan week strip, the Log
feed, the editable Profile, HealthKit read + background delivery, push registration,
StoreKit 2 subscriptions, and the Dynamic Island Live Activity.
