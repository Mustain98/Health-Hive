"use client";

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
const GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth";

// Where Google sends the user back. Must be registered as an Authorized redirect URI
// on the OAuth client, and must match what the callback page sends to the backend.
export function googleRedirectUri() {
  return `${window.location.origin}/auth/google/callback`;
}

export default function GoogleSignInButton() {
  // No client id configured → hide the button; password login still works.
  if (!CLIENT_ID) return null;

  function startRedirect() {
    const state = crypto.randomUUID();
    sessionStorage.setItem("google_oauth_state", state);

    const params = new URLSearchParams({
      client_id: CLIENT_ID!,
      redirect_uri: googleRedirectUri(),
      response_type: "code",
      scope: "openid email profile",
      state,
      prompt: "select_account",
    });
    window.location.assign(`${GOOGLE_AUTH_URL}?${params.toString()}`);
  }

  return (
    <button
      type="button"
      onClick={startRedirect}
      className="flex w-full items-center justify-center gap-3 rounded-md border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
    >
      <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden>
        <path
          fill="#4285F4"
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1Z"
        />
        <path
          fill="#34A853"
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z"
        />
        <path
          fill="#FBBC05"
          d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84Z"
        />
        <path
          fill="#EA4335"
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A11 11 0 0 0 2.18 7.06l3.66 2.84C6.71 7.3 9.14 5.38 12 5.38Z"
        />
      </svg>
      Continue with Google
    </button>
  );
}
