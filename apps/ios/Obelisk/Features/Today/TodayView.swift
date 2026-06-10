import SwiftUI

/// The gym-morning home: readiness composite with visible inputs, plus today's
/// session card and the Start Session entry to the workhorse (PRD §2.1/§2.4).
struct TodayView: View {
    @Environment(AppModel.self) private var app
    @State private var readiness: ReadinessDTO?
    @State private var session: SessionDTO?
    @State private var presentingSession = false

    private var todayString: String {
        String(ISO8601DateFormatter().string(from: Date()).prefix(10))
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    readinessCard
                    sessionCard
                }
                .padding(16)
            }
            .background(Theme.background)
            .navigationTitle("Today")
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbar {
                if app.blocks.count > 1 {
                    ToolbarItem(placement: .topBarTrailing) { blockPicker }
                }
            }
            .task { readiness = try? await NetworkClient.shared.readiness(date: todayString) }
            .task(id: app.activeBlockId) { await loadSession() }
            .task { await maybeSyncHealth() }
            .fullScreenCover(isPresented: $presentingSession) {
                InSessionView(session: session ?? SampleData.session())
            }
        }
    }

    private var blockPicker: some View {
        @Bindable var app = app
        return Menu {
            ForEach(app.blocks) { b in
                Button {
                    app.activeBlockId = b.id
                } label: {
                    if b.id == app.activeBlockId {
                        Label(b.name, systemImage: "checkmark")
                    } else {
                        Text(b.name)
                    }
                }
            }
        } label: {
            Image(systemName: "rectangle.stack")
        }
    }

    // MARK: Readiness

    private var readinessCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("READINESS")
                .font(Theme.mono(11, weight: .semibold)).tracking(2)
                .foregroundStyle(Theme.foregroundMuted)
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text(readiness?.score.map(String.init) ?? "—")
                    .font(Theme.mono(56, weight: .semibold))
                    .foregroundStyle(scoreColor)
                VStack(alignment: .leading, spacing: 2) {
                    Text(readiness?.band.capitalized ?? "No data")
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundStyle(Theme.foreground)
                    Text(readiness?.guidance ?? "Connect Apple Health to see readiness.")
                        .font(.system(size: 12))
                        .foregroundStyle(Theme.foregroundMuted)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            if let factors = readiness?.factors, !factors.isEmpty {
                Divider().overlay(Theme.borderSubtle)
                ForEach(factors) { f in
                    HStack {
                        Text(f.label).font(.system(size: 13)).foregroundStyle(Theme.foreground)
                        Spacer()
                        Text(f.value).font(Theme.mono(12)).foregroundStyle(Theme.foregroundMuted)
                    }
                }
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    private var scoreColor: Color {
        switch readiness?.score ?? -1 {
        case 80...: return Theme.primaryAccent
        case 60..<80: return Theme.foreground
        case 0..<40: return Theme.error
        case 40..<60: return Theme.copper
        default: return Theme.foregroundMuted
        }
    }

    // MARK: Session

    private var sessionCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("TODAY'S SESSION")
                .font(Theme.mono(11, weight: .semibold)).tracking(2)
                .foregroundStyle(Theme.foregroundMuted)
            Text(session?.sessionTitle ?? "Strength A")
                .font(.system(size: 22, weight: .semibold))
                .foregroundStyle(Theme.foreground)
            let exercises = session?.exercises ?? SampleData.session().exercises
            ForEach(exercises.prefix(4)) { e in
                HStack {
                    Text(e.label).font(.system(size: 13)).foregroundStyle(Theme.foregroundMuted)
                    Spacer()
                    if !e.sets.isEmpty {
                        Text("\(e.sets.count) sets").font(Theme.mono(11))
                            .foregroundStyle(Theme.foregroundMuted)
                    }
                }
            }
            Button { presentingSession = true } label: {
                Text("Start Session")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(Theme.background)
                    .frame(maxWidth: .infinity).frame(height: 52)
                    .background(Theme.primaryAccent)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .padding(.top, 4)
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    // MARK: Load

    private func loadSession() async {
        guard let blockId = app.activeBlockId else { return }
        session = try? await NetworkClient.shared.session(blockId: blockId, date: todayString)
    }

    /// First-run HealthKit permission + sync. Gated on having a backend identity,
    /// and respects a decline by not re-prompting for 7 days (PRD §2.2).
    private func maybeSyncHealth() async {
        guard AppConfig.authConfigured, HealthKitSync.isAvailable else { return }
        let key = "healthkit.lastPrompt"
        let last = UserDefaults.standard.object(forKey: key) as? Date
        if let last, Date().timeIntervalSince(last) < 7 * 24 * 3600 {
            await HealthKitSync.shared.syncRecent()  // already authorized; just sync
            return
        }
        UserDefaults.standard.set(Date(), forKey: key)
        if await HealthKitSync.shared.requestAuthorization() {
            await HealthKitSync.shared.syncRecent()
        }
    }
}
