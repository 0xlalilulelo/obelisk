import Foundation

/// A self-contained sample session so the In-Session workhorse is demonstrable in
/// the simulator before Clerk sign-in + block selection land (a later milestone).
enum SampleData {
    static func session() -> SessionDTO {
        let today = ISO8601DateFormatter().string(from: Date()).prefix(10)
        return SessionDTO(
            blockId: "sample-block",
            date: String(today),
            globalWeek: 1,
            weekInWave: 1,
            waveNum: 1,
            day: "Mon",
            sessionTitle: "Strength A",
            isRestDay: false,
            exercises: [
                PrescribedExerciseDTO(
                    label: "Back Squat — main",
                    kind: "main",
                    liftKey: "back_squat",
                    note: nil,
                    restDefaultSec: 180,
                    sets: [
                        PrescribedSetDTO(setIndex: 1, pct: 0.65, reps: 5, amrap: false, weightLb: 145),
                        PrescribedSetDTO(setIndex: 2, pct: 0.75, reps: 5, amrap: false, weightLb: 165),
                        PrescribedSetDTO(setIndex: 3, pct: 0.85, reps: 5, amrap: true, weightLb: 185),
                    ],
                    priorSets: [
                        LoggedSetDTO(setIndex: 1, weightLb: 145, reps: 5, rpe: 7, occurredAt: nil),
                        LoggedSetDTO(setIndex: 2, weightLb: 165, reps: 5, rpe: 8, occurredAt: nil),
                        LoggedSetDTO(setIndex: 3, weightLb: 185, reps: 6, rpe: 9, occurredAt: nil),
                    ]
                ),
                PrescribedExerciseDTO(
                    label: "Strict Press — accessory",
                    kind: "accessory",
                    liftKey: "strict_press",
                    note: nil,
                    restDefaultSec: 90,
                    sets: [
                        PrescribedSetDTO(setIndex: 1, pct: 0.6, reps: 8, amrap: false, weightLb: 95),
                        PrescribedSetDTO(setIndex: 2, pct: 0.6, reps: 8, amrap: false, weightLb: 95),
                        PrescribedSetDTO(setIndex: 3, pct: 0.6, reps: 8, amrap: false, weightLb: 95),
                    ],
                    priorSets: []
                ),
                PrescribedExerciseDTO(
                    label: "Pull-ups",
                    kind: "note",
                    liftKey: nil,
                    note: "Strict pull-ups, 4×5 with a 5-lb belt (or bodyweight).",
                    restDefaultSec: 90,
                    sets: [],
                    priorSets: []
                ),
            ]
        )
    }
}
