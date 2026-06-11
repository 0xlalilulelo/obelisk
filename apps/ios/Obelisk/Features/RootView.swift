import SwiftUI

/// Five-tab shell (Today / Plan / Coach / Log / Profile). The active Block is
/// shared via an `AppModel` in the environment so every tab agrees on it.
struct RootView: View {
    /// Present when Clerk is active; nil in dev/sample mode.
    var onSignOut: (() -> Void)?

    @State private var app = AppModel()

    var body: some View {
        TabView {
            TodayView()
                .tabItem { Label("Today", systemImage: "sun.max") }
            PlanView()
                .tabItem { Label("Plan", systemImage: "calendar") }
            CoachView()
                .tabItem { Label("Coach", systemImage: "bubble.left.and.text.bubble.right") }
            LogView()
                .tabItem { Label("Log", systemImage: "list.bullet.rectangle") }
            ProfileView(onSignOut: onSignOut)
                .tabItem { Label("Profile", systemImage: "person") }
        }
        .environment(app)
        .task {
            if !app.loaded { await app.loadBlocks() }
        }
    }
}

/// Shared empty state when no Block is selected yet.
struct NoBlockState: View {
    let message: String
    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: "square.stack.3d.up.slash")
                .font(.system(size: 36))
                .foregroundStyle(Theme.foregroundMuted)
            Text(message)
                .font(.system(size: 14))
                .foregroundStyle(Theme.foregroundMuted)
                .multilineTextAlignment(.center)
        }
        .padding(32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.background)
    }
}
