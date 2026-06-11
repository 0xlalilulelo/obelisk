import Foundation
import SwiftData

/// A logged set, written locally the instant the athlete confirms it (ADR-009).
/// `synced` flips true once the backend acknowledges it. `clientId` is the
/// idempotency key the server dedups on, so re-flushing is always safe.
@Model
final class PendingSet {
    @Attribute(.unique) var clientId: String
    var blockId: String?
    var sessionDate: String
    var exercise: String
    var liftKey: String?
    var setIndex: Int
    var weightLb: Double
    var reps: Int
    var rpe: Double?
    var occurredAt: Date
    var synced: Bool

    init(
        clientId: String = UUID().uuidString,
        blockId: String?,
        sessionDate: String,
        exercise: String,
        liftKey: String?,
        setIndex: Int,
        weightLb: Double,
        reps: Int,
        rpe: Double?,
        occurredAt: Date = Date(),
        synced: Bool = false
    ) {
        self.clientId = clientId
        self.blockId = blockId
        self.sessionDate = sessionDate
        self.exercise = exercise
        self.liftKey = liftKey
        self.setIndex = setIndex
        self.weightLb = weightLb
        self.reps = reps
        self.rpe = rpe
        self.occurredAt = occurredAt
        self.synced = synced
    }

    var dto: SetLogDTO {
        SetLogDTO(
            clientId: clientId,
            blockId: blockId,
            sessionDate: sessionDate,
            exercise: exercise,
            liftKey: liftKey,
            setIndex: setIndex,
            weightLb: weightLb,
            reps: reps,
            rpe: rpe,
            completed: true,
            occurredAt: ISO8601DateFormatter().string(from: occurredAt)
        )
    }
}
