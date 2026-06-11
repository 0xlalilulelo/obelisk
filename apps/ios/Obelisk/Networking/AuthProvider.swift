import Foundation

/// Single seam between the app's identity layer and the network client. The
/// handler returns a fresh bearer token for each request — Clerk's
/// `getToken()` mints a short-lived JWT, so we always ask rather than cache.
/// Defaults to the dev token (Clerk-less CI / sample runs) until Clerk wires in.
actor AuthProvider {
    static let shared = AuthProvider()

    private var handler: @Sendable () async -> String? = {
        let dev = AppConfig.devBearerToken
        return dev.isEmpty ? nil : dev
    }

    func setHandler(_ handler: @escaping @Sendable () async -> String?) {
        self.handler = handler
    }

    func token() async -> String? {
        await handler()
    }
}
