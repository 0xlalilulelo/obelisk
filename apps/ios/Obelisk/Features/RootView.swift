import SwiftUI

/// Five-tab shell (Today / Plan / Coach / Log / Profile). Today is built out;
/// the rest are placeholders this milestone — Coach SSE chat, the Plan week
/// strip, the Log feed, and the editable Profile land next.
struct RootView: View {
    var body: some View {
        TabView {
            TodayView()
                .tabItem { Label("Today", systemImage: "sun.max") }
            PlaceholderTab(title: "Plan", systemImage: "calendar",
                           detail: "Your 12-week Block, week by week.")
                .tabItem { Label("Plan", systemImage: "calendar") }
            PlaceholderTab(title: "Coach", systemImage: "bubble.left.and.text.bubble.right",
                           detail: "Chat with the Block Coach to adapt your plan.")
                .tabItem { Label("Coach", systemImage: "bubble.left.and.text.bubble.right") }
            PlaceholderTab(title: "Log", systemImage: "list.bullet.rectangle",
                           detail: "Every set you've logged, synced from the gym.")
                .tabItem { Label("Log", systemImage: "list.bullet.rectangle") }
            PlaceholderTab(title: "Profile", systemImage: "person",
                           detail: "Your athlete profile, integrations, and plan.")
                .tabItem { Label("Profile", systemImage: "person") }
        }
    }
}

struct PlaceholderTab: View {
    let title: String
    let systemImage: String
    let detail: String

    var body: some View {
        NavigationStack {
            VStack(spacing: 12) {
                Image(systemName: systemImage)
                    .font(.system(size: 40))
                    .foregroundStyle(Theme.foregroundMuted)
                Text(detail)
                    .font(.system(size: 14))
                    .foregroundStyle(Theme.foregroundMuted)
                    .multilineTextAlignment(.center)
                Text("Coming in a later Phase 2 milestone")
                    .font(Theme.mono(11)).foregroundStyle(Theme.borderSubtle)
            }
            .padding(32)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Theme.background)
            .navigationTitle(title)
            .toolbarColorScheme(.dark, for: .navigationBar)
        }
    }
}
