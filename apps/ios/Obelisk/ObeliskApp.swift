import ClerkKit
import SwiftData
import SwiftUI

/// App entry. Hosts the SwiftData container for the offline set-log queue
/// (ADR-009) and the five-tab shell.
@main
struct ObeliskApp: App {
    init() {
        ClerkBootstrap.configureIfEnabled()
    }
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
            Group {
                if AppConfig.clerkPublishableKey != nil {
                    ClerkGate().environment(Clerk.shared)
                } else {
                    // Clerk-less mode (CI / sample data): the dev token drives auth.
                    RootView()
                }
            }
            .preferredColorScheme(.dark)
            .tint(Theme.primaryAccent)
        }
        .modelContainer(container)
    }
}
