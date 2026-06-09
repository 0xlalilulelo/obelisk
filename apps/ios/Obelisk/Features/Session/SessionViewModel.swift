import Foundation
import SwiftData
import SwiftUI

/// One editable set row in the In-Session screen. Pre-filled from last session's
/// actuals when present, else the prescription (PRD §2.1).
struct SetRow: Identifiable {
    let id = UUID()
    let setIndex: Int
    let prescribedWeight: Int?
    let prescribedReps: Int
    let amrap: Bool
    let priorWeight: Double?
    let priorReps: Int?
    var weight: Double
    var reps: Int
    var rpe: Double?
    var logged: Bool = false
}

/// UI state for one exercise in the session.
struct ExerciseUI: Identifiable {
    let id: String
    let label: String
    let kind: String
    let liftKey: String?
    let note: String?
    let restDefaultSec: Int
    var rows: [SetRow]
    /// e1RM to beat for PR detection; filled from GET /v1/athlete/pr/{lift}.
    var prBest: Int?

    var isLoggable: Bool { !rows.isEmpty }
}

/// Drives the In-Session screen: pre-fill, set logging (optimistic local write +
/// sync), the rest timer, and PR detection.
@Observable
@MainActor
final class SessionViewModel {
    let session: SessionDTO
    var exercises: [ExerciseUI]
    var currentIndex: Int = 0

    // Rest timer — stored as an end date so the countdown is drift-free.
    var restEndDate: Date?
    var restTotalSec: Int = 0

    var prToast: String?
    var showPlateCalcForRow: UUID?

    init(session: SessionDTO) {
        self.session = session
        self.exercises = session.exercises.map { ex in
            let priorByIndex = Dictionary(
                ex.priorSets.map { ($0.setIndex, $0) }, uniquingKeysWith: { a, _ in a }
            )
            let rows = ex.sets.map { s -> SetRow in
                let prior = priorByIndex[s.setIndex]
                let weight = prior?.weightLb ?? Double(s.weightLb ?? 0)
                let reps = prior?.reps ?? s.reps
                return SetRow(
                    setIndex: s.setIndex,
                    prescribedWeight: s.weightLb,
                    prescribedReps: s.reps,
                    amrap: s.amrap,
                    priorWeight: prior?.weightLb,
                    priorReps: prior?.reps,
                    weight: weight,
                    reps: reps,
                    rpe: prior?.rpe
                )
            }
            return ExerciseUI(
                id: ex.id, label: ex.label, kind: ex.kind, liftKey: ex.liftKey,
                note: ex.note, restDefaultSec: ex.restDefaultSec, rows: rows, prBest: nil
            )
        }
        // Start on the first loggable exercise.
        currentIndex = exercises.firstIndex(where: \.isLoggable) ?? 0
    }

    var currentExercise: ExerciseUI? {
        exercises.indices.contains(currentIndex) ? exercises[currentIndex] : nil
    }

    var loggableExercises: [ExerciseUI] { exercises.filter(\.isLoggable) }

    // MARK: Mutation

    func adjustWeight(exercise exId: String, row rowId: UUID, by delta: Double) {
        mutate(exId, rowId) { $0.weight = max(0, $0.weight + delta) }
    }

    func adjustReps(exercise exId: String, row rowId: UUID, by delta: Int) {
        mutate(exId, rowId) { $0.reps = max(0, $0.reps + delta) }
    }

    func setRPE(exercise exId: String, row rowId: UUID, to rpe: Double?) {
        mutate(exId, rowId) { $0.rpe = rpe }
    }

    func copyPrevious(exercise exId: String, row rowId: UUID) {
        guard let ei = exercises.firstIndex(where: { $0.id == exId }),
              let ri = exercises[ei].rows.firstIndex(where: { $0.id == rowId }),
              ri > 0 else { return }
        let prev = exercises[ei].rows[ri - 1]
        mutate(exId, rowId) { $0.weight = prev.weight; $0.reps = prev.reps; $0.rpe = prev.rpe }
    }

    private func mutate(_ exId: String, _ rowId: UUID, _ change: (inout SetRow) -> Void) {
        guard let ei = exercises.firstIndex(where: { $0.id == exId }),
              let ri = exercises[ei].rows.firstIndex(where: { $0.id == rowId }) else { return }
        change(&exercises[ei].rows[ri])
    }

    // MARK: Logging

    /// Confirm a set: optimistic local write, start rest, detect PR, kick a sync.
    func logSet(exercise exId: String, row rowId: UUID, context: ModelContext) {
        guard let ei = exercises.firstIndex(where: { $0.id == exId }),
              let ri = exercises[ei].rows.firstIndex(where: { $0.id == rowId }) else { return }
        var row = exercises[ei].rows[ri]
        let ex = exercises[ei]

        context.insert(PendingSet(
            blockId: session.blockId,
            sessionDate: session.date,
            exercise: ex.label,
            liftKey: ex.liftKey,
            setIndex: row.setIndex,
            weightLb: row.weight,
            reps: row.reps,
            rpe: row.rpe
        ))
        try? context.save()

        row.logged = true
        exercises[ei].rows[ri] = row
        Haptics.setLogged()

        detectPR(exerciseIndex: ei, row: row)
        startRest(seconds: ex.restDefaultSec)

        Task { await SyncEngine(context: context).flush() }
    }

    func deleteRow(exercise exId: String, row rowId: UUID) {
        guard let ei = exercises.firstIndex(where: { $0.id == exId }) else { return }
        exercises[ei].rows.removeAll { $0.id == rowId }
    }

    private func detectPR(exerciseIndex ei: Int, row: SetRow) {
        let e1 = Strength.e1rm(weightLb: row.weight, reps: row.reps)
        guard let best = exercises[ei].prBest, e1 > best else { return }
        exercises[ei].prBest = e1
        prToast = "New \(exercises[ei].label) e1RM: \(e1) lb"
        Haptics.personalRecord()
    }

    // MARK: Rest timer

    func startRest(seconds: Int) {
        restTotalSec = seconds
        restEndDate = Date().addingTimeInterval(Double(seconds))
    }

    func adjustRest(by seconds: Int) {
        guard let end = restEndDate else { return }
        restEndDate = max(Date(), end.addingTimeInterval(Double(seconds)))
    }

    func skipRest() {
        restEndDate = nil
        Haptics.restDone()
    }

    /// Load PR baselines so the first logged set can already register a record.
    func loadPRBaselines() async {
        for (i, ex) in exercises.enumerated() {
            guard let lift = ex.liftKey else { continue }
            if let pr = try? await NetworkClient.shared.pr(lift: lift) {
                exercises[i].prBest = pr.e1rm
            }
        }
    }
}
