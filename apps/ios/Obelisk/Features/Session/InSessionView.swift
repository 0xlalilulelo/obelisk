import SwiftData
import SwiftUI

#if canImport(UIKit)
import UIKit
#endif

/// The highest-stakes screen (PRD §2.1): full-screen set logging with pre-filled
/// values, auto-starting rest timer, inline plate calculator, and PR haptics.
struct InSessionView: View {
    @Environment(\.modelContext) private var context
    @Environment(\.dismiss) private var dismiss

    @State private var vm: SessionViewModel
    @State private var transientToast: String?
    @State private var showEndPrompt = false
    @State private var sessionRPE: Double = 7

    init(session: SessionDTO) {
        _vm = State(initialValue: SessionViewModel(session: session))
    }

    private var exercise: ExerciseUI? { vm.currentExercise }

    var body: some View {
        ZStack(alignment: .bottom) {
            Theme.background.ignoresSafeArea()

            VStack(spacing: 0) {
                topBar
                if let ex = exercise, ex.isLoggable {
                    ScrollView {
                        VStack(spacing: 20) {
                            hero(ex)
                            setRows(ex)
                            if let note = ex.note { noteCard(note) }
                        }
                        .padding(16)
                        .padding(.bottom, 96)
                    }
                } else {
                    Spacer()
                    Text("Rest day — nothing to log.")
                        .foregroundStyle(Theme.foregroundMuted)
                    Spacer()
                }
                Spacer(minLength: 0)
            }
            bottomBar
            if let toast = transientToast ?? vm.prToast { toastView(toast) }
        }
        .onAppear {
            setIdleTimer(disabled: true)
            Task { await vm.loadPRBaselines() }
        }
        .onDisappear { setIdleTimer(disabled: false) }
        .sheet(isPresented: restPresented) {
            if let end = vm.restEndDate {
                RestTimerView(
                    endDate: end,
                    totalSec: vm.restTotalSec,
                    onAdjust: { vm.adjustRest(by: $0) },
                    onSkip: { vm.skipRest() }
                )
                .presentationDetents([.fraction(0.4)])
                .presentationDragIndicator(.visible)
                .presentationBackground(Theme.surface)
            }
        }
        .confirmationDialog("End session?", isPresented: $showEndPrompt, titleVisibility: .visible) {
            ForEach([6, 7, 8, 9, 10], id: \.self) { rpe in
                Button("Session RPE \(rpe)") { endSession(rpe: rpe) }
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("How hard was today overall?")
        }
        .onChange(of: vm.prToast) { _, new in
            guard new != nil else { return }
            Task { try? await Task.sleep(for: .seconds(2)); vm.prToast = nil }
        }
    }

    // MARK: Top bar

    private var topBar: some View {
        let ex = exercise
        let nextSet = ex?.rows.first(where: { !$0.logged })?.setIndex ?? (ex?.rows.count ?? 0)
        let count = ex?.rows.count ?? 0
        return VStack(spacing: 4) {
            HStack {
                iconButton("xmark") { dismiss() }
                Spacer()
                Text(ex?.label ?? vm.session.sessionTitle)
                    .font(Theme.mono(17, weight: .semibold))
                    .foregroundStyle(Theme.foreground)
                    .lineLimit(1)
                Spacer()
                iconButton("arrow.left.arrow.right") { cycleExercise() }
            }
            if count > 0 {
                Text("Set \(min(nextSet, count)) of \(count)")
                    .font(Theme.mono(12))
                    .foregroundStyle(Theme.foregroundMuted)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Theme.surface)
    }

    // MARK: Hero

    private func hero(_ ex: ExerciseUI) -> some View {
        let row = ex.rows.first(where: { !$0.logged }) ?? ex.rows.last
        return VStack(spacing: 6) {
            if let row {
                Text("\(Int(row.weight)) lb × \(row.reps)\(row.amrap ? "+" : "")")
                    .font(Theme.mono(44, weight: .semibold))
                    .foregroundStyle(Theme.foreground)
                if let pw = row.priorWeight, let pr = row.priorReps {
                    Text("last time · \(Int(pw)) × \(pr)")
                        .font(Theme.mono(12))
                        .foregroundStyle(Theme.foregroundMuted)
                } else if let presc = row.prescribedWeight {
                    Text("prescribed · \(presc) × \(row.prescribedReps)")
                        .font(Theme.mono(12))
                        .foregroundStyle(Theme.foregroundMuted)
                }
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 24)
        .background(Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    // MARK: Set rows

    private func setRows(_ ex: ExerciseUI) -> some View {
        VStack(spacing: 10) {
            ForEach(ex.rows) { row in
                setRow(ex, row)
            }
        }
    }

    private func setRow(_ ex: ExerciseUI, _ row: SetRow) -> some View {
        VStack(spacing: 10) {
            HStack(spacing: 10) {
                Text("\(row.setIndex)")
                    .font(Theme.mono(15, weight: .semibold))
                    .foregroundStyle(Theme.foregroundMuted)
                    .frame(width: 22)

                stepper(value: "\(Int(row.weight))", unit: "lb",
                        minus: { vm.adjustWeight(exercise: ex.id, row: row.id, by: -2.5) },
                        plus: { vm.adjustWeight(exercise: ex.id, row: row.id, by: 2.5) },
                        tap: { togglePlateCalc(row.id) })

                stepper(value: "\(row.reps)", unit: "rep",
                        minus: { vm.adjustReps(exercise: ex.id, row: row.id, by: -1) },
                        plus: { vm.adjustReps(exercise: ex.id, row: row.id, by: 1) })

                rpeChip(ex, row)

                checkbox(logged: row.logged) {
                    vm.logSet(exercise: ex.id, row: row.id, context: context)
                }
            }
            if vm.showPlateCalcForRow == row.id {
                PlateCalcPanel(target: row.weight)
            }
        }
        .padding(12)
        .background(row.logged ? Theme.surfaceElevated : Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(
            RoundedRectangle(cornerRadius: 8).stroke(Theme.borderSubtle, lineWidth: 1)
        )
        .swipeActions(edge: .leading) {
            Button { vm.copyPrevious(exercise: ex.id, row: row.id) } label: {
                Label("Same as prev", systemImage: "arrow.uturn.up")
            }.tint(Theme.primary)
        }
        .swipeActions(edge: .trailing) {
            Button(role: .destructive) {
                vm.deleteRow(exercise: ex.id, row: row.id)
            } label: { Label("Delete", systemImage: "trash") }
        }
    }

    private func stepper(
        value: String, unit: String,
        minus: @escaping () -> Void, plus: @escaping () -> Void, tap: (() -> Void)? = nil
    ) -> some View {
        HStack(spacing: 4) {
            tapButton("minus", action: minus)
            Button(action: { tap?() }) {
                VStack(spacing: 0) {
                    Text(value).font(Theme.mono(18, weight: .semibold))
                    Text(unit).font(Theme.mono(9)).foregroundStyle(Theme.foregroundMuted)
                }
                .frame(minWidth: 48)
            }
            .buttonStyle(.plain)
            .foregroundStyle(Theme.foreground)
            tapButton("plus", action: plus)
        }
    }

    // 56pt tap targets per spec.
    private func tapButton(_ icon: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 15, weight: .bold))
                .frame(width: 40, height: 56)
                .background(Theme.surfaceElevated)
                .clipShape(RoundedRectangle(cornerRadius: 6))
        }
        .buttonStyle(.plain)
        .foregroundStyle(Theme.foreground)
    }

    private func rpeChip(_ ex: ExerciseUI, _ row: SetRow) -> some View {
        Menu {
            Button("—") { vm.setRPE(exercise: ex.id, row: row.id, to: nil) }
            ForEach([6.0, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0], id: \.self) { v in
                Button(String(format: "%.1f", v)) { vm.setRPE(exercise: ex.id, row: row.id, to: v) }
            }
        } label: {
            Text(row.rpe.map { String(format: "%.1f", $0) } ?? "RPE")
                .font(Theme.mono(12, weight: .semibold))
                .foregroundStyle(row.rpe == nil ? Theme.foregroundMuted : Theme.copper)
                .frame(width: 44, height: 56)
                .background(Theme.surfaceElevated)
                .clipShape(RoundedRectangle(cornerRadius: 6))
        }
    }

    private func checkbox(logged: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: logged ? "checkmark.circle.fill" : "circle")
                .font(.system(size: 28))
                .foregroundStyle(logged ? Theme.primaryAccent : Theme.foregroundMuted)
                .frame(width: 56, height: 56)
        }
        .buttonStyle(.plain)
    }

    private func noteCard(_ note: String) -> some View {
        Text(note)
            .font(.system(size: 13))
            .foregroundStyle(Theme.foregroundMuted)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(12)
            .background(Theme.surface)
            .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    // MARK: Bottom bar

    private var bottomBar: some View {
        HStack(spacing: 12) {
            iconButton("mic.fill") { transientToast = "Voice coming soon"; scheduleToastClear() }
            iconButton("bubble.left.and.text.bubble.right") {
                transientToast = "Coach opens here"; scheduleToastClear()
            }
            Spacer()
            Button { showEndPrompt = true } label: {
                Text("End session")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(Theme.background)
                    .padding(.horizontal, 20)
                    .frame(height: 48)
                    .background(Theme.primaryAccent)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(.ultraThinMaterial)
    }

    // MARK: Bits

    private func iconButton(_ icon: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(Theme.foreground)
                .frame(width: 44, height: 44)
                .background(Theme.surfaceElevated)
                .clipShape(RoundedRectangle(cornerRadius: 8))
        }
        .buttonStyle(.plain)
    }

    private func toastView(_ text: String) -> some View {
        Text(text)
            .font(.system(size: 13, weight: .medium))
            .foregroundStyle(Theme.foreground)
            .padding(.horizontal, 16).padding(.vertical, 10)
            .background(Theme.surfaceElevated)
            .clipShape(Capsule())
            .padding(.bottom, 80)
            .transition(.move(edge: .bottom).combined(with: .opacity))
    }

    private var restPresented: Binding<Bool> {
        Binding(get: { vm.restEndDate != nil }, set: { if !$0 { vm.restEndDate = nil } })
    }

    private func togglePlateCalc(_ rowId: UUID) {
        vm.showPlateCalcForRow = vm.showPlateCalcForRow == rowId ? nil : rowId
    }

    private func cycleExercise() {
        let loggable = vm.exercises.indices.filter { vm.exercises[$0].isLoggable }
        guard let pos = loggable.firstIndex(of: vm.currentIndex) else {
            vm.currentIndex = loggable.first ?? vm.currentIndex; return
        }
        vm.currentIndex = loggable[(pos + 1) % loggable.count]
    }

    private func scheduleToastClear() {
        Task { try? await Task.sleep(for: .seconds(2)); transientToast = nil }
    }

    private func endSession(rpe: Int) {
        sessionRPE = Double(rpe)
        Task {
            await SyncEngine(context: context).flush()
            dismiss()
        }
    }

    private func setIdleTimer(disabled: Bool) {
        #if canImport(UIKit)
        UIApplication.shared.isIdleTimerDisabled = disabled
        #endif
    }
}

/// Inline plate breakdown for a standard 45-lb bar (PRD §2.1).
struct PlateCalcPanel: View {
    let target: Double
    @State private var bar: Double = 45

    var body: some View {
        let result = PlateMath.perSide(target: target, bar: bar)
        return VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Plates per side").font(Theme.mono(11, weight: .semibold))
                    .foregroundStyle(Theme.foregroundMuted)
                Spacer()
                Picker("Bar", selection: $bar) {
                    Text("45").tag(45.0); Text("35").tag(35.0)
                }
                .pickerStyle(.segmented).frame(width: 120)
            }
            if result.plates.isEmpty {
                Text("Just the bar").font(Theme.mono(14)).foregroundStyle(Theme.foreground)
            } else {
                HStack(spacing: 6) {
                    ForEach(Array(result.plates.enumerated()), id: \.offset) { _, p in
                        Text(p == p.rounded() ? "\(Int(p))" : String(format: "%.1f", p))
                            .font(Theme.mono(13, weight: .semibold))
                            .foregroundStyle(Theme.background)
                            .padding(.horizontal, 8).padding(.vertical, 6)
                            .background(Theme.copper)
                            .clipShape(RoundedRectangle(cornerRadius: 4))
                    }
                }
            }
            if result.remainder > 0.01 {
                Text("(+\(String(format: "%.1f", result.remainder)) lb unmatched)")
                    .font(Theme.mono(10)).foregroundStyle(Theme.foregroundMuted)
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.background)
        .clipShape(RoundedRectangle(cornerRadius: 6))
    }
}
