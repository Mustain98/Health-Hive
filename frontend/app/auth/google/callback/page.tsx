"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { loginWithGoogle } from "@/lib/api";
import { googleRedirectUri } from "@/components/auth/GoogleSignInButton";
import { useAuth } from "@/components/providers/AuthProvider";

function GoogleCallback() {
  const router = useRouter();
  const params = useSearchParams();
  const { login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return; // guard React 18/19 double-invoke in dev
    ran.current = true;

    const code = params.get("code");
    const state = params.get("state");
    const googleError = params.get("error");

    const expected = sessionStorage.getItem("google_oauth_state");
    sessionStorage.removeItem("google_oauth_state");

    if (googleError) {
      setError("Google sign-in was cancelled.");
      return;
    }
    if (!code) {
      setError("Missing authorization code.");
      return;
    }
    if (!state || state !== expected) {
      setError("Sign-in could not be verified. Please try again.");
      return;
    }

    (async () => {
      try {
        const { access_token } = await loginWithGoogle(code, googleRedirectUri());
        await login(access_token);
        router.replace("/dashboard");
      } catch (err: any) {
        setError(err?.message || "Google sign-in failed.");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) {
    return (
      <div className="text-center space-y-4">
        <p className="text-sm text-red-600">{error}</p>
        <Link
          href="/login"
          className="inline-block text-sm font-medium text-emerald-600 hover:text-emerald-500"
        >
          Back to sign in
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3 text-gray-600">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
      <p className="text-sm">Signing you in…</p>
    </div>
  );
}

export default function GoogleCallbackPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <Suspense fallback={<div className="text-sm text-gray-500">Loading…</div>}>
        <GoogleCallback />
      </Suspense>
    </div>
  );
}
