import SwiftUI

/// The unified Log feed — logged sets synced from the gym, newest first,
/// grouped by session date (PRD §2.1 acceptance #7).
struct LogView: View {
    @State private var entries: [LogEntryDTO] = []
    @State private var loaded = false

    var body: some View {
        NavigationStack {
            Group {
                if !loaded {
                    ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if grouped.isEmpty {
                    NoBlockState(message: "No sets logged yet. Finish a session and they appear here.")
                } else {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 16) {
                            ForEach(grouped, id: \.date) { group in
                                section(group)
                            }
                        }
                        .padding(16)
                    }
                    .background(Theme.background)
                }
            }
            .navigationTitle("Log")
            .toolbarColorScheme(.dark, for: .navigationBar)
            .background(Theme.background)
            .task { await load() }
            .refreshable { await load() }
        }
    }

    private struct DaySets {
        let date: String
        let entries: [LogEntryDTO]
    }

    /// Group set entries by session date, newest first.
    private var grouped: [DaySets] {
        let sets = entries.filter { $0.type == "set" }
        let byDate = Dictionary(grouping: sets) { $0.sessionDate ?? String($0.occurredAt.prefix(10)) }
        return byDate.keys.sorted(by: >).map { DaySets(date: $0, entries: byDate[$0] ?? []) }
    }

    private func section(_ group: DaySets) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(group.date).font(Theme.mono(12, weight: .semibold))
                .foregroundStyle(Theme.foregroundMuted)
            VStack(spacing: 0) {
                ForEach(sortedEntries(group.entries)) { e in
                    HStack {
                        Text(e.exercise ?? "Set").font(.system(size: 14))
                            .foregroundStyle(Theme.foreground).lineLimit(1)
                        Spacer()
                        Text(detail(e)).font(Theme.mono(13, weight: .medium))
                            .foregroundStyle(Theme.primaryAccent)
                    }
                    .padding(.vertical, 10).padding(.horizontal, 12)
                }
            }
            .background(Theme.surface)
            .clipShape(RoundedRectangle(cornerRadius: 8))
        }
    }

    private func sortedEntries(_ es: [LogEntryDTO]) -> [LogEntryDTO] {
        es.sorted { ($0.exercise ?? "", $0.setIndex ?? 0) < ($1.exercise ?? "", $1.setIndex ?? 0) }
    }

    private func detail(_ e: LogEntryDTO) -> String {
        let w = e.weightLb.map { String(Int($0)) } ?? "—"
        let r = e.reps.map(String.init) ?? "—"
        return "\(w) × \(r)"
    }

    private func load() async {
        if let page = try? await NetworkClient.shared.logFeed(type: "set", limit: 200) {
            entries = page.entries
        }
        loaded = true
    }
}
