import StoreKit
import SwiftUI

/// Plus product ids (must match App Store Connect + the bundled StoreKit config).
private let plusProductIDs = ["obelisk.plus.monthly", "obelisk.plus.annual"]

@Observable
@MainActor
final class StoreModel {
    var products: [Product] = []
    var tier = "free"
    var working = false
    var message: String?

    func load() async {
        tier = (try? await NetworkClient.shared.subscription().tier) ?? "free"
        products = ((try? await Product.products(for: plusProductIDs)) ?? [])
            .sorted { $0.price < $1.price }
    }

    /// Purchase, then hand the signed transaction to the backend (server-side
    /// verification is the source of truth — we never self-grant from the client).
    func purchase(_ product: Product) async {
        working = true
        defer { working = false }
        do {
            let result = try await product.purchase()
            switch result {
            case let .success(verification):
                let sub = try await NetworkClient.shared.verifyApple(
                    signedTransaction: verification.jwsRepresentation
                )
                tier = sub.tier
                if case let .verified(transaction) = verification {
                    await transaction.finish()
                }
                message = "You're on \(sub.tier.capitalized)."
            case .userCancelled:
                break
            default:
                message = "Purchase pending."
            }
        } catch {
            message = "Purchase failed. Please try again."
        }
    }

    /// Re-sync the current entitlement to the backend (Restore Purchases).
    func restore() async {
        working = true
        defer { working = false }
        for await result in Transaction.currentEntitlements {
            if case let .verified(transaction) = result,
                plusProductIDs.contains(transaction.productID) {
                if let sub = try? await NetworkClient.shared.verifyApple(
                    signedTransaction: result.jwsRepresentation
                ) {
                    tier = sub.tier
                    message = "Restored \(sub.tier.capitalized)."
                }
                return
            }
        }
        message = "No active purchase to restore."
    }
}

struct StorePlanView: View {
    @State private var store = StoreModel()

    var body: some View {
        Form {
            Section {
                LabeledContent("Current plan", value: store.tier.capitalized)
            }

            if store.tier == "plus" {
                Section {
                    Text("You have full access — unlimited Blocks, HealthKit sync, and unlimited Coach chat.")
                        .font(.system(size: 13)).foregroundStyle(Theme.foregroundMuted)
                    Link("Manage subscription", destination: manageURL)
                }
            } else {
                Section("Upgrade to Plus") {
                    if store.products.isEmpty {
                        Text("Products unavailable. Check your App Store connection.")
                            .font(.system(size: 13)).foregroundStyle(Theme.foregroundMuted)
                    }
                    ForEach(store.products, id: \.id) { product in
                        Button {
                            Task { await store.purchase(product) }
                        } label: {
                            HStack {
                                VStack(alignment: .leading) {
                                    Text(product.displayName)
                                    Text(product.description).font(.caption)
                                        .foregroundStyle(Theme.foregroundMuted)
                                }
                                Spacer()
                                Text(product.displayPrice).fontWeight(.semibold)
                            }
                        }
                        .disabled(store.working)
                    }
                }
                Section {
                    Button("Restore Purchases") { Task { await store.restore() } }
                        .disabled(store.working)
                }
            }

            if let message = store.message {
                Section { Text(message).font(.system(size: 13)).foregroundStyle(Theme.primaryAccent) }
            }
        }
        .scrollContentBackground(.hidden)
        .background(Theme.background)
        .navigationTitle("Plan")
        .toolbarColorScheme(.dark, for: .navigationBar)
        .task { await store.load() }
    }

    private var manageURL: URL {
        URL(string: "https://apps.apple.com/account/subscriptions")!
    }
}
