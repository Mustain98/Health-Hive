"use client";

import { ReactNode } from "react";
import { useAuth } from "./AuthGuard";

interface ConsultantGuardProps {
    children: ReactNode;
}

export default function ConsultantGuard({ children }: ConsultantGuardProps) {
    const { user, loading } = useAuth();

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    if (!user) {
        return null; // AuthGuard should handle redirect if likely wrapped, or we can redirect here too. 
        // But usually ConsultantGuard is used inside protected routes. 
        // Ideally, we might want to redirect if not logged in, but let's assume AuthGuard wraps it or handles it.
        // Actually, let's just show access denied or similar if not logged in but loaded?
        // If we are here and not loading, and no user, we are probably not logged in.
    }

    if (user.user_type !== "consultant") {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
                <div className="max-w-md w-full text-center">
                    <h2 className="text-2xl font-bold text-gray-900 mb-4">Access Denied</h2>
                    <p className="text-gray-600 mb-6">
                        This page is only accessible to verified consultants.
                    </p>
                    <a
                        href="/dashboard"
                        className="inline-block px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
                    >
                        Go to Dashboard
                    </a>
                </div>
            </div>
        );
    }

    return <>{children}</>;
}
