import Foundation

enum APIError: Error, LocalizedError {
    case http(Int, String)
    case decoding(String)

    var errorDescription: String? {
        switch self {
        case let .http(code, body): return "HTTP \(code): \(body)"
        case let .decoding(msg): return "Decoding failed: \(msg)"
        }
    }
}

/// Thin async client over the `/v1` API. An actor so request/decoding work is
/// serialized off the main thread; views call its async methods directly.
actor NetworkClient {
    static let shared = NetworkClient()

    private let session: URLSession
    private let baseURL: URL
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder
    // Strategy-free coders for types that declare their own snake_case keys
    // (ProfileDTO — see ProfileModels for why).
    private let rawDecoder = JSONDecoder()
    private let rawEncoder = JSONEncoder()

    init(session: URLSession = .shared, baseURL: URL = AppConfig.apiBaseURL) {
        self.session = session
        self.baseURL = baseURL
        decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
    }

    // MARK: Reads

    func session(blockId: String, date: String) async throws -> SessionDTO {
        try await get("/v1/blocks/\(blockId)/sessions/\(date)")
    }

    func readiness(date: String) async throws -> ReadinessDTO {
        try await get("/v1/athlete/readiness?date=\(date)")
    }

    func pr(lift: String) async throws -> PRDTO {
        try await get("/v1/athlete/pr/\(lift)")
    }

    func blocks() async throws -> [BlockSummaryDTO] {
        try await get("/v1/blocks")
    }

    func profile() async throws -> ProfileDTO {
        let req = request("/v1/athlete/profile", method: "GET", token: await AuthProvider.shared.token())
        return try await performRaw(req)
    }

    @discardableResult
    func upsertProfile(_ p: ProfileDTO) async throws -> ProfileDTO {
        var req = request("/v1/athlete/profile", method: "POST", token: await AuthProvider.shared.token())
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try rawEncoder.encode(p)
        return try await performRaw(req)
    }

    func notificationPrefs() async throws -> NotificationPrefsDTO {
        try await get("/v1/notifications/preferences")
    }

    @discardableResult
    func updateNotificationPrefs(_ patch: NotificationPrefsPatch) async throws -> NotificationPrefsDTO {
        try await send("/v1/notifications/preferences", method: "PATCH", body: patch)
    }

    @discardableResult
    func registerDevice(token deviceToken: String) async throws -> NotificationPrefsDTO {
        try await send("/v1/notifications/register", method: "POST", body: ["device_token": deviceToken])
    }

    func subscription() async throws -> SubscriptionDTO {
        try await get("/v1/subscription")
    }

    @discardableResult
    func verifyApple(signedTransaction: String) async throws -> SubscriptionDTO {
        try await send(
            "/v1/subscription/apple/verify",
            method: "POST",
            body: ["signed_transaction": signedTransaction],
        )
    }

    func logFeed(type: String? = nil, limit: Int = 50) async throws -> LogPageDTO {
        let q = type.map { "&type=\($0)" } ?? ""
        return try await get("/v1/log?limit=\(limit)\(q)")
    }

    func messages(blockId: String) async throws -> MessagePageDTO {
        try await get("/v1/blocks/\(blockId)/messages?limit=100")
    }

    func plan(blockId: String) async throws -> PlanResponseDTO {
        try await get("/v1/blocks/\(blockId)/plan")
    }

    @discardableResult
    func commitEdit(blockId: String, editId: String) async throws -> EmptyDTO {
        try await postNoBody("/v1/blocks/\(blockId)/edits/\(editId)/commit")
    }

    @discardableResult
    func rejectEdit(blockId: String, editId: String) async throws -> EmptyDTO {
        try await postNoBody("/v1/blocks/\(blockId)/edits/\(editId)/reject")
    }

    // MARK: SSE chat (ADR-006)

    /// Stream a chat turn. Yields parsed events; finishes (throwing) on transport
    /// error. Cancelling the consuming task cancels the request.
    func streamChat(blockId: String, message: String) -> AsyncThrowingStream<ChatEvent, Error> {
        AsyncThrowingStream { continuation in
            let work = Task {
                do {
                    let token = await AuthProvider.shared.token()
                    var req = request("/v1/blocks/\(blockId)/chat", method: "POST", token: token)
                    req.setValue("application/json", forHTTPHeaderField: "Content-Type")
                    req.setValue("text/event-stream", forHTTPHeaderField: "Accept")
                    req.httpBody = try encoder.encode(ChatInDTO(message: message))

                    let (bytes, resp) = try await session.bytes(for: req)
                    guard let http = resp as? HTTPURLResponse,
                        (200..<300).contains(http.statusCode)
                    else {
                        throw APIError.http((resp as? HTTPURLResponse)?.statusCode ?? -1, "chat failed")
                    }

                    var event = "message"
                    var data: [String] = []
                    for try await raw in bytes.lines {
                        let line = raw.trimmingCharacters(in: CharacterSet(charactersIn: "\r"))
                        if line.isEmpty {
                            if let ev = NetworkClient.parseFrame(event: event, data: data.joined(separator: "\n")) {
                                continuation.yield(ev)
                            }
                            event = "message"
                            data = []
                        } else if line.hasPrefix("event:") {
                            event = String(line.dropFirst(6)).trimmingCharacters(in: .whitespaces)
                        } else if line.hasPrefix("data:") {
                            data.append(String(line.dropFirst(5)).trimmingCharacters(in: .whitespaces))
                        }
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
            continuation.onTermination = { _ in work.cancel() }
        }
    }

    nonisolated static func parseFrame(event: String, data: String) -> ChatEvent? {
        guard let d = data.data(using: .utf8),
            let obj = try? JSONSerialization.jsonObject(with: d) as? [String: Any]
        else { return nil }
        switch event {
        case "open": return .open
        case "tool_use": return .toolUse(obj["name"] as? String ?? "")
        case "token": return .token(obj["text"] as? String ?? "")
        case "plan_edit":
            return .planEdit(
                editId: obj["edit_id"] as? String ?? "", diff: obj["diff"] as? String ?? ""
            )
        case "done": return .done
        case "error": return .error(obj["message"] as? String ?? "error")
        default: return nil
        }
    }

    // MARK: Writes

    @discardableResult
    func postLog(_ batch: LogBatchDTO) async throws -> LogBatchResultDTO {
        try await send("/v1/log", method: "POST", body: batch)
    }

    @discardableResult
    func ingestHealthKit(_ batch: WearableBatchDTO) async throws -> WearableBatchResultDTO {
        try await send("/v1/wearable/healthkit", method: "POST", body: batch)
    }

    // MARK: Plumbing

    private func get<T: Decodable>(_ path: String) async throws -> T {
        try await perform(request(path, method: "GET", token: await AuthProvider.shared.token()))
    }

    private func postNoBody<T: Decodable>(_ path: String) async throws -> T {
        try await perform(request(path, method: "POST", token: await AuthProvider.shared.token()))
    }

    private func send<B: Encodable, T: Decodable>(
        _ path: String, method: String, body: B
    ) async throws -> T {
        var req = request(path, method: method, token: await AuthProvider.shared.token())
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try encoder.encode(body)
        return try await perform(req)
    }

    private func request(_ path: String, method: String, token: String?) -> URLRequest {
        // Concatenate (not appendingPathComponent) so query strings survive — the
        // path already starts with "/" and baseURL has no trailing slash.
        let url = URL(string: baseURL.absoluteString + path) ?? baseURL
        var req = URLRequest(url: url)
        req.httpMethod = method
        if let token, !token.isEmpty {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return req
    }

    private func perform<T: Decodable>(_ req: URLRequest) async throws -> T {
        let (data, resp) = try await session.data(for: req)
        guard let http = resp as? HTTPURLResponse else {
            throw APIError.http(-1, "no response")
        }
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.http(http.statusCode, String(data: data, encoding: .utf8) ?? "")
        }
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding("\(error)")
        }
    }

    /// Like `perform` but with the strategy-free decoder (for ProfileDTO).
    private func performRaw<T: Decodable>(_ req: URLRequest) async throws -> T {
        let (data, resp) = try await session.data(for: req)
        guard let http = resp as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw APIError.http(
                (resp as? HTTPURLResponse)?.statusCode ?? -1,
                String(data: data, encoding: .utf8) ?? ""
            )
        }
        do {
            return try rawDecoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding("\(error)")
        }
    }
}
