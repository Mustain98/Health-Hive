// frontend/app/(auth)/register/page.tsx
"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

type RegisterPayload = {
  email: string;
  password: string;
  full_name: string;
};

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState<RegisterPayload>({
    email: "",
    password: "",
    full_name: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      await apiFetch("/api/auth/register", {
        method: "POST",
        body: JSON.stringify(form),
      });

      setSuccessMsg("Account created! Redirecting to login...");
      setTimeout(() => router.push("/login"), 1500);
    } catch (err: any) {
      setError(err.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-md space-y-6">
        <h1 className="text-2xl font-bold text-center">Create your account</h1>

        {error && (
          <p className="text-sm text-red-600 border border-red-200 bg-red-50 rounded-md px-3 py-2">
            {error}
          </p>
        )}
        {successMsg && (
          <p className="text-sm text-green-700 border border-green-200 bg-green-50 rounded-md px-3 py-2">
            {successMsg}
          </p>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Full name"
            type="text"
            value={form.full_name}
            onChange={(e) =>
              setForm((f) => ({ ...f, full_name: e.target.value }))
            }
            required
          />

          <Input
            label="Email"
            type="email"
            value={form.email}
            onChange={(e) =>
              setForm((f) => ({ ...f, email: e.target.value }))
            }
            required
          />

          <Input
            label="Password"
            type="password"
            value={form.password}
            onChange={(e) =>
              setForm((f) => ({ ...f, password: e.target.value }))
            }
            required
          />

          <Button type="submit" className="w-full" loading={loading}>
            Sign up
          </Button>
        </form>

        <p className="text-xs text-center text-gray-500">
          Already have an account?{" "}
          <Link href="/login" className="text-blue-600 hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </main>
  );
}
