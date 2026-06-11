import Foundation

/// App-wide state shared across tabs — chiefly the athlete's blocks and which one
/// is active. Injected into the environment by RootView so Today / Plan / Coach /
/// Log all read the same selection.
@Observable
@MainActor
final class AppModel {
    var blocks: [BlockSummaryDTO] = []
    var activeBlockId: String?
    var loaded = false

    var activeBlock: BlockSummaryDTO? { blocks.first { $0.id == activeBlockId } }

    func loadBlocks() async {
        defer { loaded = true }
        guard let fetched = try? await NetworkClient.shared.blocks(), !fetched.isEmpty else {
            // Dev/sample fallback so the UI is navigable without a backend.
            if activeBlockId == nil { activeBlockId = AppConfig.devBlockId }
            return
        }
        blocks = fetched
        if activeBlockId == nil || !fetched.contains(where: { $0.id == activeBlockId }) {
            activeBlockId = fetched.first { $0.phase == "active" }?.id ?? fetched.first?.id
        }
    }
}
