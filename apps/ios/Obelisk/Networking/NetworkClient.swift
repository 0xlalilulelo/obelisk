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
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init(session: URLSession = .shared) {
        self.session = session
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

    private func send<B: Encodable, T: Decodable>(
        _ path: String, method: String, body: B
    ) async throws -> T {
        var req = request(path, method: method, token: await AuthProvider.shared.token())
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try encoder.encode(body)
        return try await perform(req)
    }

    private func request(_ path: String, method: String, token: String?) -> URLRequest {
        var req = URLRequest(url: AppConfig.apiBaseURL.appendingPathComponent(path))
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
}
