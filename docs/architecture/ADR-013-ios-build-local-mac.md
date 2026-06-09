# ADR-013: iOS built on a local Mac (supersedes ADR-007's constraint)

**Status:** Accepted · **Date:** 2026-06-09 · **Supersedes the premise of** ADR-007

## Context

ADR-007 deferred the iOS app to "a dedicated session" and CI-only builds because Phase 1
development was on Windows, which can't run Xcode. As a result the Phase 1 iOS scaffold
(5-tab shell, Clerk sign-in, Today/Coach/Log) was **never built** — `apps/ios` is a README.
Phase 2's headline features (In-Session, HealthKit, push, StoreKit) all assume that
scaffold exists. Phase 2 development moved to a Mac (Xcode 26.5, Swift 6.3.2, iOS 26
simulators).

## Decision

- **Build the iOS app locally on the Mac**, simulator-verified each step, instead of
  blind CI-only iteration. The Phase 1 scaffold is built first as the foundation, then
  Phase 2 layers onto it — In-Session is the highest-stakes screen and ships first.
- **`ios.yml` is the gate, not the only build.** The workflow stays, but its pins are
  refreshed from the dead `Xcode_15.4` / iOS 17 targets to the toolchain actually
  installed; local `xcodebuild`/simulator runs are the inner loop.
- **Hardware-only acceptance is explicitly human-in-the-loop.** TestFlight on a real
  iPhone with HealthKit flowing from a real Apple Watch, live StoreKit/Stripe/APNs, and
  the App Store Connect product config require device + account access the build agent
  doesn't have. These are handed back as verifiable checkpoints, not automated.

## Consequences

- ADR-007's "no local Mac" premise no longer holds; its CI wiring survives as a guard.
- The Phase 1 iOS scope is absorbed into Phase 2's first iOS milestone (it was a gap, not
  a completed layer) — sequencing reflects that.
- Backend Phase 2 endpoints were built first precisely because they're fully verifiable in
  this environment and unblock both iOS and desktop.
