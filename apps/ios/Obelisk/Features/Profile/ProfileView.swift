import SwiftUI

/// Editable athlete profile + notification preferences + integrations + sign out
/// (PRD §2.6 settings surface, iOS side).
struct ProfileView: View {
    var onSignOut: (() -> Void)?

    @State private var draft = ProfileDTO(
        name: "", age: 30, sex: nil, bodyweightLb: nil, heightIn: nil, restingHrBpm: nil,
        estimated1rm: [:], primaryGoals: [], equipment: "full_gym", daysPerWeek: 3,
        primaryModality: "hybrid"
    )
    @State private var goalsText = ""
    @State private var prefs: NotificationPrefsDTO?
    @State private var loaded = false
    @State private var saving = false
    @State private var savedTick = false

    private let modalities = ["strength", "hybrid", "endurance", "climbing", "tactical"]
    private let equipments = ["bodyweight", "minimal", "home_gym", "full_gym"]

    var body: some View {
        NavigationStack {
            Form {
                profileSection
                if let prefs { notificationsSection(prefs) }
                integrationsSection
                Section {
                    NavigationLink {
                        StorePlanView()
                    } label: {
                        LabeledContent("Plan", value: "Manage")
                    }
                }
                if let onSignOut {
                    Section {
                        Button(role: .destructive, action: onSignOut) { Text("Sign out") }
                    }
                }
            }
            .scrollContentBackground(.hidden)
            .background(Theme.background)
            .navigationTitle("Profile")
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(action: save) {
                        if saving { ProgressView() }
                        else { Text(savedTick ? "Saved" : "Save").fontWeight(.semibold) }
                    }
                    .disabled(saving || draft.name.isEmpty)
                }
            }
            .task { await load() }
        }
    }

    private var profileSection: some View {
        Section("Athlete") {
            LabeledContent("Name") {
                TextField("Name", text: $draft.name).multilineTextAlignment(.trailing)
            }
            Stepper("Age \(draft.age)", value: $draft.age, in: 13...100)
            LabeledContent("Bodyweight (lb)") {
                TextField("lb", value: $draft.bodyweightLb, format: .number)
                    .keyboardType(.decimalPad).multilineTextAlignment(.trailing)
            }
            Stepper("Days / week: \(draft.daysPerWeek)", value: $draft.daysPerWeek, in: 1...7)
            Picker("Modality", selection: $draft.primaryModality) {
                ForEach(modalities, id: \.self) { Text($0.capitalized).tag($0) }
            }
            Picker("Equipment", selection: $draft.equipment) {
                ForEach(equipments, id: \.self) { Text($0.replacingOccurrences(of: "_", with: " ").capitalized).tag($0) }
            }
            VStack(alignment: .leading, spacing: 4) {
                Text("Goals (comma-separated)").font(.caption).foregroundStyle(Theme.foregroundMuted)
                TextField("e.g. bench priority, finger strength", text: $goalsText, axis: .vertical)
            }
        }
    }

    private func notificationsSection(_ p: NotificationPrefsDTO) -> some View {
        Section("Notifications") {
            Toggle("Morning session ping", isOn: bind(\.morningPingEnabled, p.morningPingEnabled) {
                NotificationPrefsPatch(morningPingEnabled: $0, morningPingTime: nil,
                                       weeklyRecapEnabled: nil, eventNotificationsEnabled: nil)
            })
            Toggle("Sunday weekly recap", isOn: bind(\.weeklyRecapEnabled, p.weeklyRecapEnabled) {
                NotificationPrefsPatch(morningPingEnabled: nil, morningPingTime: nil,
                                       weeklyRecapEnabled: $0, eventNotificationsEnabled: nil)
            })
            Toggle("Event alerts (PRs, deloads)", isOn: bind(\.eventNotificationsEnabled, p.eventNotificationsEnabled) {
                NotificationPrefsPatch(morningPingEnabled: nil, morningPingTime: nil,
                                       weeklyRecapEnabled: nil, eventNotificationsEnabled: $0)
            })
            LabeledContent("Morning ping", value: p.morningPingTime)
            LabeledContent("Quiet hours", value: "\(p.quietHoursStart)–\(p.quietHoursEnd)")
        }
    }

    private var integrationsSection: some View {
        Section("Integrations") {
            LabeledContent("Apple Health", value: "Read-only")
            LabeledContent("Strava", value: "Coming soon")
        }
    }

    // MARK: Logic

    /// A Toggle binding that optimistically updates local prefs and PATCHes.
    private func bind(
        _ keyPath: WritableKeyPath<NotificationPrefsDTO, Bool>,
        _ current: Bool,
        _ patch: @escaping (Bool) -> NotificationPrefsPatch
    ) -> Binding<Bool> {
        Binding(
            get: { prefs?[keyPath: keyPath] ?? current },
            set: { newValue in
                prefs?[keyPath: keyPath] = newValue
                Task { prefs = try? await NetworkClient.shared.updateNotificationPrefs(patch(newValue)) }
            }
        )
    }

    private func load() async {
        async let p = NetworkClient.shared.profile()
        async let n = NetworkClient.shared.notificationPrefs()
        if let loadedProfile = try? await p {
            draft = loadedProfile
            goalsText = loadedProfile.primaryGoals.joined(separator: ", ")
        }
        prefs = try? await n
        loaded = true
    }

    private func save() {
        saving = true
        savedTick = false
        draft.primaryGoals = goalsText
            .split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
        Task {
            if let updated = try? await NetworkClient.shared.upsertProfile(draft) {
                draft = updated
                savedTick = true
            }
            saving = false
        }
    }
}
