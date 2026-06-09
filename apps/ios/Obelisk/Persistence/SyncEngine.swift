import Foundation
import SwiftData

/// Flushes locally-queued sets to the backend. Idempotent by construction
/// (server dedups on `clientId`), so a flush that partially fails is simply
/// retried whole on the next trigger: app foreground, after a set is logged,
/// and at end-of-session.
@MainActor
struct SyncEngine {
    let context: ModelContext

    /// Push every not-yet-synced set; mark the ones the server accepted.
    func flush() async {
        let unsynced = (try? context.fetch(
            FetchDescriptor<PendingSet>(predicate: #Predicate { !$0.synced })
        )) ?? []
        guard !unsynced.isEmpty else { return }

        let batch = LogBatchDTO(sets: unsynced.map(\.dto))
        do {
            _ = try await NetworkClient.shared.postLog(batch)
            for row in unsynced { row.synced = true }
            try? context.save()
        } catch {
            // Leave rows unsynced; the next trigger retries. Never drop a set.
        }
    }

    var pendingCount: Int {
        (try? context.fetchCount(
            FetchDescriptor<PendingSet>(predicate: #Predicate { !$0.synced })
        )) ?? 0
    }
}
