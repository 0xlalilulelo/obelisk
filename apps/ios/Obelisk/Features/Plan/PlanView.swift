import SwiftUI

/// The Block at a glance: title + a week strip of the day template (PRD §6.3).
struct PlanView: View {
    @Environment(AppModel.self) private var app
    @State private var plan: PlanResponseDTO?

    var body: some View {
        NavigationStack {
            Group {
                if let blockId = app.activeBlockId {
                    content(blockId: blockId)
                } else {
                    NoBlockState(message: "No active Block yet.")
                }
            }
            .navigationTitle("Plan")
            .toolbarColorScheme(.dark, for: .navigationBar)
        }
    }

    private func content(blockId: String) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let cycle = plan?.plan {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(cycle.title).font(.system(size: 22, weight: .semibold))
                            .foregroundStyle(Theme.foreground)
                        if let sub = cycle.subtitle {
                            Text(sub).font(.system(size: 13)).foregroundStyle(Theme.foregroundMuted)
                        }
                    }
                    Text("WEEK TEMPLATE").font(Theme.mono(11, weight: .semibold)).tracking(1.5)
                        .foregroundStyle(Theme.foregroundMuted)
                    ForEach(cycle.dayTemplate) { day in
                        DayRow(day: day)
                    }
                } else if plan != nil {
                    Text("This Block has no plan yet.")
                        .font(.system(size: 14)).foregroundStyle(Theme.foregroundMuted)
                } else {
                    ProgressView().frame(maxWidth: .infinity).padding(.top, 40)
                }
            }
            .padding(16)
        }
        .background(Theme.background)
        .task(id: blockId) { plan = try? await NetworkClient.shared.plan(blockId: blockId) }
    }
}

private struct DayRow: View {
    let day: PlanDayDTO

    var body: some View {
        HStack(spacing: 12) {
            Text(day.day.uppercased())
                .font(Theme.mono(12, weight: .semibold))
                .foregroundStyle(day.isRest ? Theme.foregroundMuted : Theme.primaryAccent)
                .frame(width: 40, alignment: .leading)
            VStack(alignment: .leading, spacing: 2) {
                Text(day.session).font(.system(size: 15, weight: .medium))
                    .foregroundStyle(Theme.foreground)
                if day.liftCount > 0 {
                    Text("\(day.liftCount) main/accessory lift\(day.liftCount == 1 ? "" : "s")")
                        .font(Theme.mono(11)).foregroundStyle(Theme.foregroundMuted)
                } else if let note = day.blocks.first?.note {
                    Text(note).font(Theme.mono(11)).foregroundStyle(Theme.foregroundMuted)
                        .lineLimit(1)
                }
            }
            Spacer()
        }
        .padding(12)
        .background(Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}
