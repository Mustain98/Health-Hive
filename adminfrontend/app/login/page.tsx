"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { loginWithToken } from "../../lib/api";
import { useAuth } from "../../components/providers/AuthProvider";

const C = {
    blue: "#2563eb",
    white: "#ffffff",
    gray50: "#f9fafb",
    gray200: "#e5e7eb",
    gray500: "#6b7280",
    gray900: "#111827",
};

export default function LoginPage() {
    const router = useRouter();
    const { login } = useAuth();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);

        try {
            const data = await loginWithToken(email, password);
            await login(data.access_token);
            router.push("/admin");
        } catch (err: any) {
            setError(err?.message || "Invalid credentials or unauthorized.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            display: "flex", alignItems: "center", justifyContent: "center",
            minHeight: "100vh", backgroundColor: C.gray50,
            fontFamily: "'Geist', 'DM Sans', sans-serif"
        }}>
            <div style={{
                backgroundColor: C.white, padding: "40px", borderRadius: "12px",
                boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)", width: "100%", maxWidth: "400px"
            }}>
                <div style={{ textAlign: "center", marginBottom: "32px" }}>
                    <h1 style={{ fontSize: "24px", fontWeight: 700, margin: "0 0 8px", color: C.gray900 }}>HealthHive Admin</h1>
                    <p style={{ fontSize: "14px", color: C.gray500, margin: 0 }}>Sign in to the administrative dashboard</p>
                </div>

                <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                    {error && (
                        <div style={{ padding: "12px", backgroundColor: "#fef2f2", color: "#dc2626", borderRadius: "6px", fontSize: "14px", textAlign: "center" }}>
                            {error}
                        </div>
                    )}

                    <div>
                        <label style={{ display: "block", fontSize: "13px", fontWeight: 600, color: C.gray900, marginBottom: "6px" }}>Email Address</label>
                        <input
                            type="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            style={{
                                width: "100%", padding: "10px 14px", borderRadius: "8px",
                                border: `1px solid ${C.gray200}`, outline: "none", fontSize: "14px"
                            }}
                            placeholder="admin@healthhive.com"
                        />
                    </div>

                    <div>
                        <label style={{ display: "block", fontSize: "13px", fontWeight: 600, color: C.gray900, marginBottom: "6px" }}>Password</label>
                        <input
                            type="password"
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            style={{
                                width: "100%", padding: "10px 14px", borderRadius: "8px",
                                border: `1px solid ${C.gray200}`, outline: "none", fontSize: "14px"
                            }}
                            placeholder="••••••••"
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            width: "100%", padding: "12px", backgroundColor: C.blue, color: C.white,
                            border: "none", borderRadius: "8px", fontSize: "14px", fontWeight: 600,
                            cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1,
                            marginTop: "8px"
                        }}
                    >
                        {loading ? "Signing in..." : "Sign In"}
                    </button>
                </form>
            </div>
        </div>
    );
}
