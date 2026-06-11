import Foundation

/// Environment configuration. The base URL + a dev bearer token come from the
/// build environment so the simulator can hit a local backend without bundling
/// secrets. Real Clerk sign-in replaces `devBearerToken` in a later iOS milestone
/// (ADR-004 / ADR-013).
enum AppConfig {
    static var apiBaseURL: URL {
        if let raw = Bundle.main.object(forInfoDictionaryKey: "OBELISK_API_URL") as? String,
           let url = URL(string: raw) {
            return url
        }
        return URL(string: "http://localhost:8000")!
    }

    /// Dev-only bearer token used until Clerk sign-in lands. Empty in CI.
    static var devBearerToken: String {
        (Bundle.main.object(forInfoDictionaryKey: "OBELISK_DEV_TOKEN") as? String) ?? ""
    }

    /// Active block id for the Today session fetch, until block selection lands.
    /// Nil → Today falls back to the bundled sample session.
    static var devBlockId: String? {
        let raw = Bundle.main.object(forInfoDictionaryKey: "OBELISK_DEV_BLOCK_ID") as? String
        return (raw?.isEmpty == false) ? raw : nil
    }

    /// Clerk publishable key. When present the app uses real Clerk sign-in; when
    /// absent (CI / sample-data simulator runs) it falls back to the dev token.
    static var clerkPublishableKey: String? {
        let raw = Bundle.main.object(forInfoDictionaryKey: "CLERK_PUBLISHABLE_KEY") as? String
        return (raw?.isEmpty == false) ? raw : nil
    }

    /// True when the app has some way to authenticate to the backend — gates
    /// flows (like the HealthKit prompt) that are pointless without a logged-in
    /// athlete to attach data to.
    static var authConfigured: Bool {
        clerkPublishableKey != nil || !devBearerToken.isEmpty
    }
}
