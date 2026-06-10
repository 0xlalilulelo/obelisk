import Foundation

/// Codable mirrors of the backend `/v1` schemas (apps/api domain/schemas.py).
/// Dates that the API sends as calendar strings ("YYYY-MM-DD") are kept as
/// `String` here to avoid JSONDecoder date-strategy ambiguity; timestamps are
/// decoded as `String` too and parsed at the edges where needed.

// MARK: Session prescription (GET /v1/blocks/{id}/sessions/{date})

struct SessionDTO: Codable, Sendable {
    let blockId: String
    let date: String
    let globalWeek: Int
    let weekInWave: Int
    let waveNum: Int
    let day: String
    let sessionTitle: String
    let isRestDay: Bool
    let exercises: [PrescribedExerciseDTO]
}

struct PrescribedExerciseDTO: Codable, Sendable, Identifiable {
    let label: String
    let kind: String          // "main" | "accessory" | "note"
    let liftKey: String?
    let note: String?
    let restDefaultSec: Int
    let sets: [PrescribedSetDTO]
    let priorSets: [LoggedSetDTO]

    var id: String { liftKey ?? label }
}

struct PrescribedSetDTO: Codable, Sendable {
    let setIndex: Int
    let pct: Double
    let reps: Int
    let amrap: Bool
    let weightLb: Int?
}

struct LoggedSetDTO: Codable, Sendable {
    let setIndex: Int
    let weightLb: Double
    let reps: Int
    let rpe: Double?
    let occurredAt: String?
}

// MARK: Set logging (POST /v1/log)

struct SetLogDTO: Codable, Sendable {
    let clientId: String
    let blockId: String?
    let sessionDate: String
    let exercise: String
    let liftKey: String?
    let setIndex: Int
    let weightLb: Double
    let reps: Int
    let rpe: Double?
    let completed: Bool
    let occurredAt: String?
}

struct LogBatchDTO: Codable, Sendable {
    let sets: [SetLogDTO]
}

struct LogBatchResultDTO: Codable, Sendable {
    let received: Int
    let inserted: Int
    let duplicates: Int
}

// MARK: Readiness (GET /v1/athlete/readiness)

struct ReadinessDTO: Codable, Sendable {
    let date: String
    let score: Int?
    let band: String
    let guidance: String
    let factors: [ReadinessFactorDTO]
}

struct ReadinessFactorDTO: Codable, Sendable, Identifiable {
    let key: String
    let label: String
    let value: String
    let score: Int
    let weight: Double
    var id: String { key }
}

// MARK: Log feed (GET /v1/log)

struct LogEntryDTO: Codable, Sendable, Identifiable {
    let id: String
    let type: String
    let occurredAt: String
    let source: String
}

struct LogPageDTO: Codable, Sendable {
    let entries: [LogEntryDTO]
    let total: Int
}

// MARK: Blocks (GET /v1/blocks)

struct BlockSummaryDTO: Codable, Sendable, Identifiable {
    let id: String
    let name: String
    let goal: String
    let programModel: String
    let phase: String
    let startDate: String?
    let endDate: String?
    let createdAt: String
}

// MARK: Wearable ingest (POST /v1/wearable/healthkit)

struct WearableSampleInDTO: Codable, Sendable {
    let sampleUuid: String
    let source: String
    let sampleType: String
    let occurredAt: String
    let durationSec: Int?
    let value: Double?
    let unit: String?
}

struct WearableBatchDTO: Codable, Sendable {
    let samples: [WearableSampleInDTO]
}

struct WearableBatchResultDTO: Codable, Sendable {
    let received: Int
    let inserted: Int
    let duplicates: Int
}

// MARK: PR (GET /v1/athlete/pr/{lift})

struct PRDTO: Codable, Sendable {
    let lift: String
    let e1rm: Int?
    let source: String
    let weightLb: Double?
    let reps: Int?
    let occurredAt: String?
}
