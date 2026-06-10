import Foundation

/// Athlete profile (GET/POST /v1/athlete/profile). Uses explicit snake_case keys
/// and is (de)coded with raw coders — the shared convertFromSnakeCase strategy
/// can't round-trip `estimated_1rm` (the digit defeats camel↔snake conversion).
struct ProfileDTO: Codable, Sendable {
    var name: String
    var age: Int
    var sex: String?
    var bodyweightLb: Double?
    var heightIn: Double?
    var restingHrBpm: Int?
    var estimated1rm: [String: Double]
    var primaryGoals: [String]
    var equipment: String
    var daysPerWeek: Int
    var primaryModality: String

    enum CodingKeys: String, CodingKey {
        case name, age, sex, equipment
        case bodyweightLb = "bodyweight_lb"
        case heightIn = "height_in"
        case restingHrBpm = "resting_hr_bpm"
        case estimated1rm = "estimated_1rm"
        case primaryGoals = "primary_goals"
        case daysPerWeek = "days_per_week"
        case primaryModality = "primary_modality"
    }
}

/// Notification preferences (GET/PATCH /v1/notifications/preferences). These keys
/// round-trip cleanly through the shared snake_case coders.
struct NotificationPrefsDTO: Codable, Sendable {
    var morningPingEnabled: Bool
    var morningPingTime: String
    var weeklyRecapEnabled: Bool
    var eventNotificationsEnabled: Bool
    var quietHoursStart: String
    var quietHoursEnd: String
    var timezone: String
    var deviceRegistered: Bool
}

/// Partial update body for preferences (only set fields change server-side).
struct NotificationPrefsPatch: Codable, Sendable {
    var morningPingEnabled: Bool?
    var morningPingTime: String?
    var weeklyRecapEnabled: Bool?
    var eventNotificationsEnabled: Bool?
}

/// Subscription state (GET /v1/subscription, POST .../apple/verify).
struct SubscriptionDTO: Codable, Sendable {
    var tier: String
    var status: String
    var source: String
    var periodEnd: String?
}
