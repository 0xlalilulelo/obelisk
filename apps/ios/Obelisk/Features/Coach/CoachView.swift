import SwiftUI

struct PendingPlanEdit: Identifiable {
    let editId: String
    let diff: String
    var id: String { editId }
}

/// Drives the Coach chat: history load, SSE streaming, and structured plan-edit
/// approval (carried from Phase 1) — accept/reject hit the commit/reject endpoints.
@Observable
@MainActor
final class CoachViewModel {
    var history: [MessageDTO] = []
    var pendingUser: String?
    var liveText = ""
    var tools: [String] = []
    var streaming = false
    var pendingEdit: PendingPlanEdit?

    func load(blockId: String) async {
        if let page = try? await NetworkClient.shared.messages(blockId: blockId) {
            history = page.messages.filter(\.isVisible)
        }
    }

    func send(blockId: String, text: String) async {
        pendingUser = text
        liveText = ""
        tools = []
        pendingEdit = nil
        streaming = true
        do {
            let stream = await NetworkClient.shared.streamChat(blockId: blockId, message: text)
            for try await ev in stream {
                switch ev {
                case let .token(t): liveText += t
                case let .toolUse(n): tools.append(n)
                case let .planEdit(id, diff): pendingEdit = PendingPlanEdit(editId: id, diff: diff)
                case let .error(m): liveText += "\n[error: \(m)]"
                case .open, .done: break
                }
            }
        } catch {
            liveText += "\n[connection lost]"
        }
        streaming = false
        pendingUser = nil
        liveText = ""
        await load(blockId: blockId)
    }

    func accept(blockId: String) async {
        guard let e = pendingEdit else { return }
        _ = try? await NetworkClient.shared.commitEdit(blockId: blockId, editId: e.editId)
        pendingEdit = nil
        await load(blockId: blockId)
    }

    func reject(blockId: String) async {
        guard let e = pendingEdit else { return }
        _ = try? await NetworkClient.shared.rejectEdit(blockId: blockId, editId: e.editId)
        pendingEdit = nil
    }
}

struct CoachView: View {
    @Environment(AppModel.self) private var app

    var body: some View {
        NavigationStack {
            Group {
                if let blockId = app.activeBlockId {
                    CoachChat(blockId: blockId)
                } else {
                    NoBlockState(message: "No active Block to coach yet.")
                }
            }
            .navigationTitle("Coach")
            .toolbarColorScheme(.dark, for: .navigationBar)
        }
    }
}

struct CoachChat: View {
    let blockId: String
    @State private var vm = CoachViewModel()
    @State private var input = ""

    var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 12) {
                        if vm.history.isEmpty && vm.pendingUser == nil && !vm.streaming {
                            Text("Ask the Coach to refine the plan, explain a decision, or adapt a week.")
                                .font(.system(size: 14))
                                .foregroundStyle(Theme.foregroundMuted)
                                .padding(.top, 12)
                        }
                        ForEach(vm.history) { m in
                            Bubble(role: m.role, text: m.content.displayText, cost: m.costUsd)
                        }
                        if let user = vm.pendingUser {
                            Bubble(role: "user", text: user, cost: nil)
                        }
                        if vm.streaming {
                            ForEach(Array(vm.tools.enumerated()), id: \.offset) { _, t in
                                HStack(spacing: 6) {
                                    Image(systemName: "wrench.and.screwdriver")
                                        .font(.system(size: 11))
                                    Text(t).font(Theme.mono(11))
                                }
                                .foregroundStyle(Theme.foregroundMuted)
                            }
                            Bubble(role: "assistant", text: vm.liveText.isEmpty ? "…" : vm.liveText, cost: nil)
                        }
                        if let edit = vm.pendingEdit {
                            PlanEditCard(
                                edit: edit,
                                onAccept: { Task { await vm.accept(blockId: blockId) } },
                                onReject: { Task { await vm.reject(blockId: blockId) } }
                            )
                        }
                        Color.clear.frame(height: 1).id("bottom")
                    }
                    .padding(16)
                }
                .onChange(of: vm.liveText) { _, _ in proxy.scrollTo("bottom") }
                .onChange(of: vm.history.count) { _, _ in proxy.scrollTo("bottom") }
            }
            inputBar
        }
        .background(Theme.background)
        .task(id: blockId) { await vm.load(blockId: blockId) }
    }

    private var inputBar: some View {
        HStack(spacing: 8) {
            TextField("Request an adjustment…", text: $input, axis: .vertical)
                .textFieldStyle(.plain)
                .lineLimit(1...4)
                .foregroundStyle(Theme.foreground)
                .padding(.horizontal, 12).padding(.vertical, 10)
                .background(Theme.surface)
                .clipShape(RoundedRectangle(cornerRadius: 10))
            Button {
                let text = input.trimmingCharacters(in: .whitespacesAndNewlines)
                guard !text.isEmpty, !vm.streaming else { return }
                input = ""
                Task { await vm.send(blockId: blockId, text: text) }
            } label: {
                Image(systemName: vm.streaming ? "ellipsis" : "arrow.up")
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(Theme.background)
                    .frame(width: 40, height: 40)
                    .background(Theme.primaryAccent)
                    .clipShape(Circle())
            }
            .disabled(vm.streaming || input.trimmingCharacters(in: .whitespaces).isEmpty)
        }
        .padding(12)
        .background(.ultraThinMaterial)
    }
}

private struct Bubble: View {
    let role: String
    let text: String
    let cost: Double?

    private var isUser: Bool { role == "user" }

    var body: some View {
        HStack {
            if isUser { Spacer(minLength: 40) }
            VStack(alignment: .leading, spacing: 4) {
                if !isUser {
                    Text("OBELISK").font(Theme.mono(10, weight: .semibold)).tracking(1.5)
                        .foregroundStyle(Theme.primaryAccent)
                }
                Text(text).font(.system(size: 15)).foregroundStyle(Theme.foreground)
                if let cost { Text(String(format: "$%.4f", cost)).font(Theme.mono(9)).foregroundStyle(Theme.foregroundMuted) }
            }
            .padding(.horizontal, 14).padding(.vertical, 10)
            .background(isUser ? Theme.surfaceElevated : Theme.surface)
            .overlay(
                RoundedRectangle(cornerRadius: 12)
                    .stroke(isUser ? Color.clear : Theme.borderSubtle, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 12))
            if !isUser { Spacer(minLength: 40) }
        }
    }
}

private struct PlanEditCard: View {
    let edit: PendingPlanEdit
    let onAccept: () -> Void
    let onReject: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Circle().fill(Theme.copper).frame(width: 8, height: 8)
                Text("PROPOSED CHANGE").font(Theme.mono(10, weight: .semibold)).tracking(1.5)
                    .foregroundStyle(Theme.foregroundMuted)
            }
            Text(edit.diff)
                .font(Theme.mono(12))
                .foregroundStyle(Theme.foreground)
                .frame(maxWidth: .infinity, alignment: .leading)
            HStack(spacing: 10) {
                Button(action: onAccept) {
                    Text("Accept").font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(Theme.background)
                        .frame(maxWidth: .infinity).frame(height: 40)
                        .background(Theme.primaryAccent)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                }
                Button(action: onReject) {
                    Text("Reject").font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(Theme.foreground)
                        .frame(maxWidth: .infinity).frame(height: 40)
                        .background(Theme.surfaceElevated)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                }
            }
        }
        .padding(14)
        .background(Theme.surface)
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Theme.copper.opacity(0.4), lineWidth: 1))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}
