import SwiftData
import XCTest

@testable import Obelisk

/// The trust-critical durability proof (PRD §2.1): an athlete must never lose a
/// set across loss-of-signal. Drives the real on-device stack — SwiftData queue,
/// SyncEngine, NetworkClient — against a *running* backend.
///
/// Requires a local backend with dev-auth:
///   cd apps/api
///   DATABASE_URL=sqlite:////tmp/obelisk_e2e.db DEV_AUTH_TOKEN=dev-e2e-token \
///     ENVIRONMENT=development uv run uvicorn obelisk_api.main:app --port 8000
/// then: xcodebuild test -scheme ObeliskE2E -destination '...'
/// Skips cleanly when the backend isn't reachable, so it never hard-fails by accident.
final class SetDurabilityE2ETests: XCTestCase {
    let liveBase = URL(string: "http://127.0.0.1:8000")!
    let deadBase = URL(string: "http://127.0.0.1:1")! // connection refused → "offline"
    let devToken = "dev-e2e-token"

    @MainActor
    func testOfflineThenReconnectLosesNoSet() async throws {
        let token = devToken
        await AuthProvider.shared.setHandler { token }

        // Skip if there's no local backend (keeps an accidental run from failing).
        let live = NetworkClient(baseURL: liveBase)
        do {
            _ = try await live.blocks()
        } catch {
            throw XCTSkip("No backend at \(liveBase) — start uvicorn with dev-auth. (\(error))")
        }

        // Fresh in-memory queue, 5 sets tagged with a unique marker.
        let container = try ModelContainer(
            for: PendingSet.self,
            configurations: ModelConfiguration(isStoredInMemoryOnly: true)
        )
        let context = container.mainContext
        let marker = UUID().uuidString
        let ids: [String] = (1...5).map { i in
            let cid = UUID().uuidString
            context.insert(PendingSet(
                clientId: cid, blockId: nil, sessionDate: "2026-06-09",
                exercise: "e2e-\(marker)", liftKey: "back_squat", setIndex: i,
                weightLb: 200 + Double(i * 5), reps: 5, rpe: 8
            ))
            return cid
        }
        try context.save()

        // OFFLINE: dead endpoint → flush fails → all 5 stay queued, none dropped.
        await SyncEngine(context: context, client: NetworkClient(baseURL: deadBase)).flush()
        XCTAssertEqual(
            SyncEngine(context: context).pendingCount, 5,
            "a set was lost while offline"
        )

        // RECONNECT: live endpoint → flush drains the queue.
        await SyncEngine(context: context, client: live).flush()
        XCTAssertEqual(
            SyncEngine(context: context).pendingCount, 0,
            "queue did not drain after reconnect"
        )

        // SERVER TRUTH: every client_id is now present in /v1/log. (Compare
        // case-insensitively — Swift's UUID string is uppercase, the backend
        // serializes UUIDs lowercase.)
        let feed = try await live.logFeed(type: "set", limit: 200)
        let serverIds = Set(feed.entries.map { $0.id.lowercased() })
        for cid in ids {
            XCTAssertTrue(
                serverIds.contains(cid.lowercased()), "set \(cid) never reached the server"
            )
        }
    }

    /// Re-flushing an already-synced batch is a no-op server-side (idempotent on
    /// client_id) — the gym-basement double-send case.
    @MainActor
    func testReflushIsIdempotent() async throws {
        let token = devToken
        await AuthProvider.shared.setHandler { token }
        let live = NetworkClient(baseURL: liveBase)
        do {
            _ = try await live.blocks()
        } catch {
            throw XCTSkip("No backend at \(liveBase).")
        }

        let cid = UUID().uuidString
        let batch = LogBatchDTO(sets: [SetLogDTO(
            clientId: cid, blockId: nil, sessionDate: "2026-06-09", exercise: "e2e-idem",
            liftKey: "back_squat", setIndex: 1, weightLb: 225, reps: 3, rpe: 8,
            completed: true, occurredAt: nil
        )])
        let first = try await live.postLog(batch)
        XCTAssertEqual(first.inserted, 1)
        let replay = try await live.postLog(batch)
        XCTAssertEqual(replay.inserted, 0)
        XCTAssertEqual(replay.duplicates, 1)
    }
}
