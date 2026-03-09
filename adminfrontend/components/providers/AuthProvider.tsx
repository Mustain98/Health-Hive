"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api";
import { getToken, setToken as setAuthToken, logout as authLogout, isAuthenticated } from "@/lib/auth";
import type { UserRead } from "@/lib/types";

interface AuthContextType {
    user: UserRead | null;
    loading: boolean;
    login: (token: string) => Promise<void>;
    logout: () => void;
    checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
    user: null,
    loading: true,
    login: async () => { },
    logout: () => { },
    checkAuth: async () => { },
});

export function AuthProvider({ children }: { children: ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const [user, setUser] = useState<UserRead | null>(null);
    const [loading, setLoading] = useState(true);

    // Initial auth check
    useEffect(() => {
        checkAuth();
    }, []);

    async function checkAuth() {
        if (!isAuthenticated()) {
            // Only set to unauthenticated, DO NOT forcefully wipe tokens here
            setUser(null);
            setLoading(false);
            return;
        }

        try {
            const userData = await apiFetch<UserRead>("/api/auth/me");
            setUser(userData);
        } catch (error) {
            console.error("Auth check failed:", error);
            if (error instanceof ApiError && error.status === 401) {
                // Only forcefully wipe if running in the browser and genuinely rejected
                if (typeof window !== 'undefined') {
                    authLogout();
                }
                setUser(null);
            }
        } finally {
            setLoading(false);
        }
    }

    async function login(token: string) {
        setAuthToken(token);
        setLoading(true);
        await checkAuth();
        // Redirect logic can be handled here or in the login page
    }

    function logout() {
        authLogout();
        setUser(null);
        router.push("/login");
    }

    return (
        <AuthContext.Provider value={{ user, loading, login, logout, checkAuth }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    return useContext(AuthContext);
}
