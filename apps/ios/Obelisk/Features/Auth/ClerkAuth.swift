import ClerkKit
import SwiftUI

/// Clerk wiring (ADR-004). All Clerk API calls live in this file so the rest of
/// the app depends only on `AuthProvider` (token) and the gate's view switch.
enum ClerkBootstrap {
    /// Called once at launch from `App.init` (which runs on the main thread). No-op
    /// when no publishable key is configured, so the app still runs against the dev
    /// token in CI / sample mode.
    static func configureIfEnabled() {
        guard let key = AppConfig.clerkPublishableKey else { return }
        MainActor.assumeIsolated {
            Clerk.configure(publishableKey: key)
        }
    }

    /// A fresh session JWT for the network layer (Clerk mints short-lived tokens).
    @MainActor
    static func currentToken() async -> String? {
        try? await Clerk.shared.auth.getToken()
    }

    @MainActor
    static func signOut() async {
        try? await Clerk.shared.auth.signOut()
    }
}

/// Chooses the screen by auth state and routes the network token through Clerk.
struct ClerkGate: View {
    @Environment(Clerk.self) private var clerk

    var body: some View {
        Group {
            if !clerk.isLoaded {
                ProgressView()
                    .controlSize(.large)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(Theme.background)
            } else if clerk.user != nil {
                RootView(onSignOut: { Task { await ClerkBootstrap.signOut() } })
            } else {
                SignInView()
            }
        }
        .task {
            // From here on, every API request carries a fresh Clerk JWT.
            await AuthProvider.shared.setHandler {
                await ClerkBootstrap.currentToken()
            }
        }
    }
}

/// Minimal email + password sign-in. On success Clerk publishes a session and the
/// gate swaps to RootView. (Email-code / OAuth flows layer on later.)
struct SignInView: View {
    @Environment(Clerk.self) private var clerk
    @State private var email = ""
    @State private var password = ""
    @State private var error: String?
    @State private var working = false

    var body: some View {
        VStack(spacing: 20) {
            Spacer()
            Text("OBELISK")
                .font(Theme.mono(28, weight: .semibold)).tracking(6)
                .foregroundStyle(Theme.foreground)
            Text("Sign in to your training")
                .font(.system(size: 14)).foregroundStyle(Theme.foregroundMuted)

            VStack(spacing: 12) {
                field("Email", text: $email, secure: false)
                    .keyboardType(.emailAddress)
                    .textInputAutocapitalization(.never)
                field("Password", text: $password, secure: true)
            }
            .padding(.top, 8)

            if let error {
                Text(error).font(.system(size: 12)).foregroundStyle(Theme.error)
                    .multilineTextAlignment(.center)
            }

            Button(action: submit) {
                Group {
                    if working { ProgressView().tint(Theme.background) }
                    else { Text("Sign in").font(.system(size: 16, weight: .semibold)) }
                }
                .foregroundStyle(Theme.background)
                .frame(maxWidth: .infinity).frame(height: 52)
                .background(Theme.primaryAccent)
                .clipShape(RoundedRectangle(cornerRadius: 8))
            }
            .disabled(working || email.isEmpty || password.isEmpty)
            Spacer()
        }
        .padding(32)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.background)
    }

    private func field(_ placeholder: String, text: Binding<String>, secure: Bool) -> some View {
        Group {
            if secure { SecureField(placeholder, text: text) }
            else { TextField(placeholder, text: text) }
        }
        .textFieldStyle(.plain)
        .foregroundStyle(Theme.foreground)
        .padding(14)
        .background(Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.borderSubtle, lineWidth: 1))
    }

    private func submit() {
        working = true
        error = nil
        Task { @MainActor in
            do {
                _ = try await clerk.auth.signInWithPassword(identifier: email, password: password)
            } catch {
                self.error = error.localizedDescription
            }
            working = false
        }
    }
}
