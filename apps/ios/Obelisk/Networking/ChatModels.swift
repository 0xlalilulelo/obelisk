import Foundation

// MARK: Chat (GET /v1/blocks/{id}/messages, POST .../chat over SSE)

struct ChatInDTO: Codable, Sendable {
    let message: String
}

/// Decodes any JSON object while ignoring its fields — for endpoints whose body
/// we don't need (commit/reject return the block/edit, but the UI just refetches).
struct EmptyDTO: Codable, Sendable {}

struct MessageDTO: Codable, Sendable, Identifiable {
    let id: String
    let role: String
    let content: JSONValue
    let costUsd: Double?
    let createdAt: String

    /// User/assistant prose only — hides tool frames (mirrors the desktop Coach).
    var isVisible: Bool {
        if role == "tool" { return false }
        if role == "user", case .array = content { return false } // tool_result frame
        return !content.displayText.isEmpty
    }
}

struct MessagePageDTO: Codable, Sendable {
    let messages: [MessageDTO]
    let total: Int
}

/// A streamed chat event (ADR-006 SSE protocol).
enum ChatEvent: Sendable {
    case open
    case toolUse(String)
    case token(String)
    case planEdit(editId: String, diff: String)
    case done
    case error(String)
}

// MARK: Plan (GET /v1/blocks/{id}/plan)

struct PlanResponseDTO: Codable, Sendable {
    let plan: CyclePlanDTO?
    let summary: String
}

/// Only the slice the iOS Plan strip renders; Codable ignores the rest.
struct CyclePlanDTO: Codable, Sendable {
    let title: String
    let subtitle: String?
    let dayTemplate: [PlanDayDTO]
}

struct PlanDayDTO: Codable, Sendable, Identifiable {
    let day: String
    let session: String
    let blocks: [PlanBlockDTO]
    var id: String { day }

    var liftCount: Int { blocks.filter { $0.kind == "main" || $0.kind == "accessory" }.count }
    var isRest: Bool { session.lowercased().contains("rest") }
}

struct PlanBlockDTO: Codable, Sendable {
    let label: String
    let kind: String
    let liftKey: String?
    let note: String?
}

// MARK: Arbitrary JSON (message content can be a string or content-block array)

enum JSONValue: Codable, Sendable {
    case string(String)
    case number(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() {
            self = .null
        } else if let b = try? c.decode(Bool.self) {
            self = .bool(b)
        } else if let n = try? c.decode(Double.self) {
            self = .number(n)
        } else if let s = try? c.decode(String.self) {
            self = .string(s)
        } else if let a = try? c.decode([JSONValue].self) {
            self = .array(a)
        } else if let o = try? c.decode([String: JSONValue].self) {
            self = .object(o)
        } else {
            self = .null
        }
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch self {
        case let .string(s): try c.encode(s)
        case let .number(n): try c.encode(n)
        case let .bool(b): try c.encode(b)
        case let .array(a): try c.encode(a)
        case let .object(o): try c.encode(o)
        case .null: try c.encodeNil()
        }
    }

    subscript(_ key: String) -> JSONValue? {
        if case let .object(o) = self { return o[key] }
        return nil
    }

    var stringValue: String? { if case let .string(s) = self { return s } else { return nil } }
    var doubleValue: Double? { if case let .number(n) = self { return n } else { return nil } }
    var intValue: Int? { if case let .number(n) = self { return Int(n) } else { return nil } }

    /// Display text: a plain string, or the concatenation of `type:"text"` blocks.
    var displayText: String {
        switch self {
        case let .string(s):
            return s
        case let .array(items):
            return items
                .compactMap { item -> String? in
                    guard case let .object(o) = item, case .string("text")? = o["type"],
                        case let .string(t)? = o["text"]
                    else { return nil }
                    return t
                }
                .joined(separator: "\n")
                .trimmingCharacters(in: .whitespacesAndNewlines)
        default:
            return ""
        }
    }
}
