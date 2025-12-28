"use client";

import { useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api";
import { isAuthenticated, logout } from "@/lib/auth";
import type { UserRead } from "@/lib/types";

interface AuthGuardProps {
    children: ReactNode;
}

export default function AuthGuard({ children }: AuthGuardProps) {
    const router = useRouter();
    const [user, setUser] = useState<UserRead | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function checkAuth() {
            // Check if token exists
            if (!isAuthenticated()) {
                router.push("/login");
                return;
            }

            try {
                // Verify token with backend
                const userData = await apiFetch<UserRead>("/api/auth/me");
                setUser(userData);
            } catch (error) {
                // Token invalid or expired
                if (error instanceof ApiError && error.status === 401) {
                    logout();
                } else {
                    console.error("Auth check failed:", error);
                    router.push("/login");
                }
            } finally {
                setLoading(false);
            }
        }

        checkAuth();
    }, [router]);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!user) {
        return null;
    }

    return <>{children}</>;
}

/**
 * Hook to get current user from context
 * Usage: const user = useAuth();
 */
export function useAuth() {
    const [user, setUser] = useState<UserRead | null>(null);

    useEffect(() => {
        async function loadUser() {
            if (isAuthenticated()) {
                try {
                    const userData = await apiFetch<UserRead>("/api/auth/me");
                    setUser(userData);
                } catch (error) {
                    console.error("Failed to load user:", error);
                }
            }
        }
        loadUser();
    }, []);

    return user;
}
