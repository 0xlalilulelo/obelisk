import Foundation

#if canImport(UIKit)
import UIKit

/// Thin wrapper over UIKit feedback generators. Per PRD §2.1: a light tap on set
/// log, success on rest-timer dismiss, and a distinct copper-pulse on a PR.
enum Haptics {
    static func setLogged() {
        UIImpactFeedbackGenerator(style: .light).impactOccurred()
    }

    static func restDone() {
        UINotificationFeedbackGenerator().notificationOccurred(.success)
    }

    /// PR pulse — a heavier double-tap so a new max feels distinct from a set log.
    static func personalRecord() {
        let gen = UIImpactFeedbackGenerator(style: .heavy)
        gen.impactOccurred(intensity: 1.0)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.12) {
            gen.impactOccurred(intensity: 1.0)
        }
    }
}
#else
enum Haptics {
    static func setLogged() {}
    static func restDone() {}
    static func personalRecord() {}
}
#endif
