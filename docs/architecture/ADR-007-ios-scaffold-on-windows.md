# ADR-007: iOS scaffolded & CI-verified (no local Mac)

**Status:** Accepted · **Date:** 2026-06-09

## Context

Phase 1 development is happening on a Windows machine. Xcode, the iOS Simulator,
and SwiftLint do not run here. The mission still requires a SwiftUI app that signs in
and renders the Today tab, with `ios.yml` building and testing it.

## Decision

- The iOS app is written as complete source (Swift/SwiftUI, `Obelisk.xcodeproj`,
  `NetworkClient` actor, `BlockCoachClient` SSE reader, Codable models hand-mirrored
  from the backend Pydantic schemas) but **its only build/test gate is `ios.yml` on a
  GitHub macOS runner** (`xcodebuild` + XCTest on an iOS 17 Simulator). Green CI is the
  proof of correctness; there is no local launch.
- Codable models are mirrored **by hand** (not `swift-openapi-generator`) for Phase 1 to
  avoid adding a code-gen toolchain we cannot run locally; revisit when a Mac is in the loop.
- Per the session plan, the iOS surface is **deferred to a dedicated session**; this ADR
  records the agreed approach so that session starts without re-deciding.

## Consequences

- iOS bugs that only surface at runtime won't be caught until CI or a Mac session.
- The hand-mirrored models can drift from the backend; a follow-up task should add a
  contract test (decode the OpenAPI examples) to catch drift in `ios.yml`.
