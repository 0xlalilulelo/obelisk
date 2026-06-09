# Obelisk iOS

Swift + SwiftUI (iOS 17+). **Deferred to a dedicated session** per the Phase 1 plan
(development is happening on Windows, which can't run Xcode). The agreed approach is
recorded in [ADR-007](../../docs/architecture/ADR-007-ios-scaffold-on-windows.md):

- Full SwiftUI source + `Obelisk.xcodeproj`, scaffolded but **built/tested only in CI**
  on a macOS runner (`xcodebuild` + XCTest on an iOS 17 Simulator) — `.github/workflows/ios.yml`
  is already wired and path-scoped to `apps/ios/**`.
- A `NetworkClient` actor + a `BlockCoachClient` SSE reader against the `/v1` API.
- Codable models hand-mirrored from the backend Pydantic schemas (see `packages/types`
  for the shapes), matching the SSE event protocol in
  [ADR-006](../../docs/architecture/ADR-006-chat-streaming-sse.md).

## Phase 1 scope (when built)

5-tab `TabView` (Today / Plan / Coach / Log / Profile): Clerk sign-in, Today tab
populated from the backend (active Block's first session), Plan week strip, a working
Coach SSE chat, an empty Log, and an editable Profile. Dark mode default.

Out of scope (Phase 2): in-session view, rest timer, voice/photo input, HealthKit,
push notifications, App Store distribution, watch app.
