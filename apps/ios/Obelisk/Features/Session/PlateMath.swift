import Foundation

/// Deterministic plate breakdown for the inline plate calculator (PRD §2.1) and
/// the Epley e1RM used for client-side PR detection. Pure + unit-tested.
enum PlateMath {
    /// Standard loadable plates (lb), heaviest first.
    static let standardPlates: [Double] = [45, 35, 25, 10, 5, 2.5]

    /// Per-side plate breakdown to reach `target` on a `bar`-lb barbell.
    /// Returns the plates for ONE side (the bar is symmetric). Leftover weight
    /// that can't be made from the plate set is returned as `remainder`.
    static func perSide(
        target: Double, bar: Double = 45, plates: [Double] = standardPlates
    ) -> (plates: [Double], remainder: Double) {
        guard target > bar else { return ([], max(0, target - bar)) }
        var perSide = (target - bar) / 2
        var result: [Double] = []
        for plate in plates {
            while perSide >= plate - 0.0001 {
                result.append(plate)
                perSide -= plate
            }
        }
        return (result, max(0, perSide))
    }
}

enum Strength {
    /// Epley estimated 1RM, rounded to the nearest 5 lb — matches the backend
    /// `compute_1rm` so client PR detection and server PR agree.
    static func e1rm(weightLb: Double, reps: Int) -> Int {
        guard weightLb > 0, reps >= 1 else { return 0 }
        let est = weightLb * (1.0 + Double(reps) / 30.0)
        return Int((est / 5.0).rounded()) * 5
    }
}
