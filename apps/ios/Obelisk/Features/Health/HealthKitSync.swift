import Foundation
import HealthKit

/// Reads recovery-relevant HealthKit samples and pushes them to the backend
/// (ADR-011). Read-only in Phase 2. The HK→DTO mapping is a pure function so it's
/// unit-tested; the queries themselves are device-verified.
@MainActor
final class HealthKitSync {
    static let shared = HealthKitSync()
    private let store = HKHealthStore()

    static var isAvailable: Bool { HKHealthStore.isHealthDataAvailable() }

    private var readTypes: Set<HKObjectType> {
        var types = Set<HKObjectType>()
        if let t = HKObjectType.quantityType(forIdentifier: .bodyMass) { types.insert(t) }
        if let t = HKObjectType.quantityType(forIdentifier: .restingHeartRate) { types.insert(t) }
        if let t = HKObjectType.quantityType(forIdentifier: .heartRateVariabilitySDNN) {
            types.insert(t)
        }
        if let t = HKObjectType.categoryType(forIdentifier: .sleepAnalysis) { types.insert(t) }
        return types
    }

    func requestAuthorization() async -> Bool {
        guard Self.isAvailable else { return false }
        do {
            try await store.requestAuthorization(toShare: [], read: readTypes)
            return true
        } catch {
            return false
        }
    }

    /// Read the last `days` of samples and POST them. Idempotent server-side, so a
    /// re-sync of the overlapping window is harmless.
    func syncRecent(days: Int = 30) async {
        guard Self.isAvailable else { return }
        let start = Calendar.current.date(byAdding: .day, value: -days, to: Date()) ?? Date()
        var samples: [WearableSampleInDTO] = []
        samples += await readQuantity(.bodyMass, type: "bodyweight", unit: .pound(), since: start)
        samples += await readQuantity(
            .restingHeartRate, type: "rhr",
            unit: HKUnit.count().unitDivided(by: .minute()), since: start
        )
        samples += await readQuantity(
            .heartRateVariabilitySDNN, type: "hrv",
            unit: HKUnit.secondUnit(with: .milli), since: start
        )
        samples += await readSleep(since: start)
        guard !samples.isEmpty else { return }
        _ = try? await NetworkClient.shared.ingestHealthKit(WearableBatchDTO(samples: samples))
    }

    // MARK: Queries

    private func readQuantity(
        _ id: HKQuantityTypeIdentifier, type: String, unit: HKUnit, since: Date
    ) async -> [WearableSampleInDTO] {
        guard let qType = HKObjectType.quantityType(forIdentifier: id) else { return [] }
        let predicate = HKQuery.predicateForSamples(withStart: since, end: Date())
        let results = await runSampleQuery(qType, predicate: predicate)
        return results.compactMap { sample in
            guard let q = sample as? HKQuantitySample else { return nil }
            return Self.makeSample(
                uuid: q.uuid.uuidString, sampleType: type,
                start: q.startDate, end: q.endDate,
                value: q.quantity.doubleValue(for: unit), unit: unit.unitString
            )
        }
    }

    private func readSleep(since: Date) async -> [WearableSampleInDTO] {
        guard let sType = HKObjectType.categoryType(forIdentifier: .sleepAnalysis) else { return [] }
        let predicate = HKQuery.predicateForSamples(withStart: since, end: Date())
        let results = await runSampleQuery(sType, predicate: predicate)
        return results.compactMap { sample in
            guard let c = sample as? HKCategorySample, Self.isAsleep(c.value) else { return nil }
            return Self.makeSample(
                uuid: c.uuid.uuidString, sampleType: "sleep",
                start: c.startDate, end: c.endDate, value: nil, unit: nil
            )
        }
    }

    private func runSampleQuery(
        _ type: HKSampleType, predicate: NSPredicate
    ) async -> [HKSample] {
        await withCheckedContinuation { cont in
            let query = HKSampleQuery(
                sampleType: type, predicate: predicate, limit: HKObjectQueryNoLimit,
                sortDescriptors: nil
            ) { _, samples, _ in
                cont.resume(returning: samples ?? [])
            }
            store.execute(query)
        }
    }

    // MARK: Pure mapping (unit-tested)

    /// Build the wire DTO. Sleep carries duration; quantities carry value+unit.
    nonisolated static func makeSample(
        uuid: String, sampleType: String, start: Date, end: Date,
        value: Double?, unit: String?
    ) -> WearableSampleInDTO {
        let duration = Int(end.timeIntervalSince(start))
        return WearableSampleInDTO(
            sampleUuid: uuid,
            source: "healthkit",
            sampleType: sampleType,
            occurredAt: ISO8601DateFormatter().string(from: start),
            durationSec: sampleType == "sleep" ? max(0, duration) : nil,
            value: value,
            unit: unit
        )
    }

    /// Treat any "asleep" sleep-analysis category as sleep time (core/deep/REM/unspecified).
    nonisolated static func isAsleep(_ raw: Int) -> Bool {
        guard let v = HKCategoryValueSleepAnalysis(rawValue: raw) else { return false }
        switch v {
        case .asleepUnspecified, .asleepCore, .asleepDeep, .asleepREM:
            return true
        default:
            return false
        }
    }
}
