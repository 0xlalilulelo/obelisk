import SwiftUI

/// The "Technical Precision / Quiet Premium" palette, hand-translated from
/// packages/design-tokens (DESIGN.md). Kept in one place so screens never
/// hardcode hex.
enum Theme {
    static let background = Color(hex: 0x0A0A0B)
    static let surface = Color(hex: 0x141416)
    static let surfaceElevated = Color(hex: 0x1C1C1F)
    static let borderSubtle = Color(hex: 0x26272B)

    static let foreground = Color(hex: 0xF4F4F5)
    static let foregroundMuted = Color(hex: 0xA1A1AA)

    static let primary = Color(hex: 0x1F4E79)
    static let primaryAccent = Color(hex: 0xA0CAFC)
    static let copper = Color(hex: 0xFFB784) // peak / PR / intensity
    static let error = Color(hex: 0xFFB4AB)

    /// Large numeric readouts use a monospaced face (weights, timers, set counts).
    static func mono(_ size: CGFloat, weight: Font.Weight = .medium) -> Font {
        .system(size: size, weight: weight, design: .monospaced)
    }
}

extension Color {
    init(hex: UInt32, alpha: Double = 1) {
        self.init(
            .sRGB,
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255,
            opacity: alpha
        )
    }
}
