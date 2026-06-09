import SwiftData
import SwiftUI

/// App entry. Hosts the SwiftData container for the offline set-log queue
/// (ADR-009) and the five-tab shell.
@main
struct ObeliskApp: App {
    /// Local-first store for logged sets. `isStoredInMemoryOnly` is off so a
    /// gym-basement session survives a force-quit before sync.
    let container: ModelContainer = {
        do {
            return try ModelContainer(for: PendingSet.self)
        } catch {
            // A broken store must not wedge the app; fall back to in-memory.
            return try! ModelContainer(
                for: PendingSet.self,
                configurations: ModelConfiguration(isStoredInMemoryOnly: true)
            )
        }
    }()

    var body: some Scene {
        WindowGroup {
            RootView()
                .preferredColorScheme(.dark)
                .tint(Theme.primaryAccent)
        }
        .modelContainer(container)
    }
}
