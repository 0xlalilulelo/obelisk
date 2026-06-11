import HealthKit
import XCTest

@testable import Obelisk

final class HealthKitMappingTests: XCTestCase {
    func testSleepSampleCarriesDuration() {
        let start = Date(timeIntervalSince1970: 0)
        let end = start.addingTimeInterval(8 * 3600)
        let dto = HealthKitSync.makeSample(
            uuid: "u1", sampleType: "sleep", start: start, end: end, value: nil, unit: nil
        )
        XCTAssertEqual(dto.sampleType, "sleep")
        XCTAssertEqual(dto.durationSec, 8 * 3600)
        XCTAssertEqual(dto.source, "healthkit")
        XCTAssertNil(dto.value)
    }

    func testQuantitySampleCarriesValueNotDuration() {
        let t = Date(timeIntervalSince1970: 1000)
        let dto = HealthKitSync.makeSample(
            uuid: "u2", sampleType: "rhr", start: t, end: t, value: 55, unit: "count/min"
        )
        XCTAssertEqual(dto.value, 55)
        XCTAssertNil(dto.durationSec)
        XCTAssertEqual(dto.unit, "count/min")
    }

    func testAsleepCategoriesCountAsSleep() {
        XCTAssertTrue(HealthKitSync.isAsleep(HKCategoryValueSleepAnalysis.asleepCore.rawValue))
        XCTAssertTrue(HealthKitSync.isAsleep(HKCategoryValueSleepAnalysis.asleepREM.rawValue))
        XCTAssertFalse(HealthKitSync.isAsleep(HKCategoryValueSleepAnalysis.awake.rawValue))
        XCTAssertFalse(HealthKitSync.isAsleep(HKCategoryValueSleepAnalysis.inBed.rawValue))
    }
}

final class PlateMathTests: XCTestCase {
    func testTwoPlatesPerSide() {
        let r = PlateMath.perSide(target: 225, bar: 45)
        XCTAssertEqual(r.plates, [45, 45])
        XCTAssertEqual(r.remainder, 0, accuracy: 0.001)
    }

    func testSinglePlate() {
        XCTAssertEqual(PlateMath.perSide(target: 135).plates, [45])
    }

    func testJustTheBar() {
        XCTAssertTrue(PlateMath.perSide(target: 45).plates.isEmpty)
    }

    func testSmallChange() {
        XCTAssertEqual(PlateMath.perSide(target: 50).plates, [2.5])
    }

    func testRemainderSurfacedWhenUnmatchable() {
        // 46 lb → 0.5 per side, not makeable from standard plates.
        let r = PlateMath.perSide(target: 46)
        XCTAssertTrue(r.plates.isEmpty)
        XCTAssertEqual(r.remainder, 0.5, accuracy: 0.001)
    }
}

final class StrengthTests: XCTestCase {
    func testEpleyMatchesBackendRounding() {
        XCTAssertEqual(Strength.e1rm(weightLb: 200, reps: 5), 235)
        XCTAssertEqual(Strength.e1rm(weightLb: 245, reps: 3), 270)
        XCTAssertEqual(Strength.e1rm(weightLb: 0, reps: 5), 0)
    }
}

final class RestTimerTests: XCTestCase {
    func testFormatMinutesSeconds() {
        XCTAssertEqual(RestTimerView.format(125), "2:05")
        XCTAssertEqual(RestTimerView.format(0), "0:00")
        XCTAssertEqual(RestTimerView.format(600), "10:00")
    }
}

final class ChatParsingTests: XCTestCase {
    func testSseFrameParsing() {
        if case .token(let t)? = NetworkClient.parseFrame(event: "token", data: #"{"text":"hi"}"#) {
            XCTAssertEqual(t, "hi")
        } else {
            XCTFail("expected token")
        }
        if case .planEdit(let id, let diff)? = NetworkClient.parseFrame(
            event: "plan_edit", data: #"{"edit_id":"e1","diff":"swap"}"#
        ) {
            XCTAssertEqual(id, "e1")
            XCTAssertEqual(diff, "swap")
        } else {
            XCTFail("expected planEdit")
        }
        if case .done? = NetworkClient.parseFrame(event: "done", data: "{}") {} else {
            XCTFail("expected done")
        }
        XCTAssertNil(NetworkClient.parseFrame(event: "unknown", data: "{}"))
    }

    func testMessageContentExtraction() throws {
        let dec = JSONDecoder()
        let plain = try dec.decode(JSONValue.self, from: Data(#""just text""#.utf8))
        XCTAssertEqual(plain.displayText, "just text")

        let blocks = try dec.decode(
            JSONValue.self,
            from: Data(#"[{"type":"text","text":"a"},{"type":"tool_use","name":"x"},{"type":"text","text":"b"}]"#.utf8)
        )
        XCTAssertEqual(blocks.displayText, "a\nb")

        let object = try dec.decode(JSONValue.self, from: Data(#"{"foo":1}"#.utf8))
        XCTAssertEqual(object.displayText, "")
    }
}

final class ProfileDTOTests: XCTestCase {
    func testRoundTripPreservesSnakeCaseKeys() throws {
        let p = ProfileDTO(
            name: "Josh", age: 34, sex: "male", bodyweightLb: 175, heightIn: 74,
            restingHrBpm: 59, estimated1rm: ["back_squat": 259], primaryGoals: ["bench"],
            equipment: "full_gym", daysPerWeek: 6, primaryModality: "hybrid"
        )
        // ProfileDTO is (de)coded with strategy-free coders (see ProfileModels).
        let data = try JSONEncoder().encode(p)
        let json = String(data: data, encoding: .utf8)!
        XCTAssertTrue(json.contains("\"estimated_1rm\""), "1rm key must survive")
        XCTAssertTrue(json.contains("\"bodyweight_lb\""))
        XCTAssertTrue(json.contains("\"primary_goals\""))

        let back = try JSONDecoder().decode(ProfileDTO.self, from: data)
        XCTAssertEqual(back.estimated1rm["back_squat"], 259)
        XCTAssertEqual(back.bodyweightLb, 175)
        XCTAssertEqual(back.daysPerWeek, 6)
    }
}

@MainActor
final class SessionViewModelTests: XCTestCase {
    func testPreFillUsesPriorActualsThenPrescription() {
        let vm = SessionViewModel(session: SampleData.session())

        // Squat has prior actuals — row 3 should pre-fill the logged 185×6, not 5.
        let squat = vm.exercises.first { $0.liftKey == "back_squat" }!
        XCTAssertEqual(squat.rows[2].weight, 185)
        XCTAssertEqual(squat.rows[2].reps, 6)

        // Strict press has no prior — falls back to prescription (95×8).
        let press = vm.exercises.first { $0.liftKey == "strict_press" }!
        XCTAssertEqual(press.rows[0].weight, 95)
        XCTAssertEqual(press.rows[0].reps, 8)
    }

    func testRestStartsFromExerciseDefault() {
        let vm = SessionViewModel(session: SampleData.session())
        XCTAssertNil(vm.restEndDate)
        vm.startRest(seconds: 180)
        XCTAssertNotNil(vm.restEndDate)
        XCTAssertEqual(vm.restTotalSec, 180)
        vm.skipRest()
        XCTAssertNil(vm.restEndDate)
    }
}
