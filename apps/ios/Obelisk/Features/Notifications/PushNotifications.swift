import HealthKit
import UIKit
import UserNotifications

/// App-lifecycle glue that can't live in the SwiftUI `App` value: APNs device-token
/// registration (PRD §2.3 / ADR-014) and HealthKit background delivery (ADR-011).
/// Both backend halves already exist — the `/v1/notifications/register` endpoint and
/// `NetworkClient.registerDevice` — so this is only the missing client wiring.
final class AppDelegate: NSObject, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        // Register the HealthKit observer queries up front so a background launch can
        // sync without any UI. No-op until the athlete has authorized HealthKit.
        HealthKitSync.shared.startBackgroundDelivery()
        return true
    }

    /// APNs issued a device token — hex-encode it and hand it to the backend, which
    /// stores it like a credential (never echoed back, ADR-014).
    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        let token = deviceToken.map { String(format: "%02x", $0) }.joined()
        Task { try? await NetworkClient.shared.registerDevice(token: token) }
    }

    func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        // Non-fatal: pushes simply won't arrive until a later launch re-registers.
    }
}

/// Notification permission + APNs registration, triggered from first-run onboarding
/// once the app has a backend identity (mirrors the HealthKit prompt gate). Self-
/// throttling: it only prompts when the status is undecided, and otherwise just
/// refreshes the token, so it's safe to call on every launch.
enum PushAuthorization {
    @MainActor
    static func requestAndRegister() async {
        let center = UNUserNotificationCenter.current()
        switch await center.notificationSettings().authorizationStatus {
        case .notDetermined:
            let granted =
                (try? await center.requestAuthorization(options: [.alert, .sound, .badge])) ?? false
            guard granted else { return }
        case .denied:
            return
        default:
            break  // authorized / provisional — fall through to (re)register the token
        }
        UIApplication.shared.registerForRemoteNotifications()
    }
}
