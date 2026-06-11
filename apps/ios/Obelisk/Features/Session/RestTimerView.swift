import SwiftUI

/// Rest countdown shown in a 0.4-detent sheet. Drives the display off an end
/// date via TimelineView so it never drifts more than the 1s tick (PRD §2.1).
struct RestTimerView: View {
    let endDate: Date
    let totalSec: Int
    let onAdjust: (Int) -> Void
    let onSkip: () -> Void

    var body: some View {
        TimelineView(.periodic(from: .now, by: 1)) { ctx in
            let remaining = max(0, Int(endDate.timeIntervalSince(ctx.date).rounded(.up)))
            VStack(spacing: 24) {
                Text("REST")
                    .font(Theme.mono(11, weight: .semibold))
                    .tracking(2)
                    .foregroundStyle(Theme.foregroundMuted)

                Text(Self.format(remaining))
                    .font(Theme.mono(96, weight: .semibold))
                    .foregroundStyle(remaining == 0 ? Theme.copper : Theme.foreground)
                    .monospacedDigit()
                    .contentTransition(.numericText())

                HStack(spacing: 12) {
                    pill("−30s") { onAdjust(-30) }
                    pill("Skip rest", filled: true) { onSkip() }
                    pill("+30s") { onAdjust(30) }
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Theme.surface)
        }
    }

    private func pill(_ title: String, filled: Bool = false, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(filled ? Theme.background : Theme.foreground)
                .padding(.horizontal, 18)
                .frame(height: 48)
                .background(filled ? Theme.primaryAccent : Theme.surfaceElevated)
                .clipShape(RoundedRectangle(cornerRadius: 8))
        }
    }

    static func format(_ seconds: Int) -> String {
        String(format: "%d:%02d", seconds / 60, seconds % 60)
    }
}
