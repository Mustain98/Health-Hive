"use client";

import AuthGuard, { useAuth } from "@/components/guards/AuthGuard";
import { getToken, logout } from "@/lib/auth";
import { useState, useEffect } from "react";

function DebugContent() {
    const user = useAuth();
    const [token, setToken] = useState<string | null>(null);
    const [decodedToken, setDecodedToken] = useState<any>(null);

    useEffect(() => {
        const currentToken = getToken();
        setToken(currentToken);

        if (currentToken) {
            try {
                // Decode JWT (just the payload, don't verify)
                const parts = currentToken.split('.');
                if (parts.length === 3) {
                    const payload = JSON.parse(atob(parts[1]));
                    setDecodedToken(payload);
                }
            } catch (e) {
                console.error("Failed to decode token:", e);
            }
        }
    }, []);

    function clearAll() {
        if (typeof window !== 'undefined') {
            localStorage.clear();
            sessionStorage.clear();
            alert("All storage cleared! Redirecting to login...");
            window.location.href = '/login';
        }
    }

    return (
        <div className="min-h-screen bg-gray-50 py-8 px-4">
            <div className="max-w-4xl mx-auto space-y-6">
                <h1 className="text-3xl font-bold">Debug Info</h1>

                {/* User Info */}
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-xl font-bold mb-4">Current User</h2>
                    {user ? (
                        <pre className="bg-gray-100 p-4 rounded overflow-x-auto text-sm">
                            {JSON.stringify(user, null, 2)}
                        </pre>
                    ) : (
                        <p className="text-gray-500">Not logged in</p>
                    )}
                </div>

                {/* Token Info */}
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-xl font-bold mb-4">Current Token</h2>
                    {token ? (
                        <div className="space-y-4">
                            <div>
                                <h3 className="font-medium text-sm text-gray-700 mb-2">Raw Token (truncated):</h3>
                                <p className="bg-gray-100 p-2 rounded text-xs font-mono break-all">
                                    {token.substring(0, 50)}...
                                </p>
                            </div>
                            {decodedToken && (
                                <div>
                                    <h3 className="font-medium text-sm text-gray-700 mb-2">Decoded Payload:</h3>
                                    <pre className="bg-gray-100 p-4 rounded overflow-x-auto text-sm">
                                        {JSON.stringify(decodedToken, null, 2)}
                                    </pre>
                                </div>
                            )}
                        </div>
                    ) : (
                        <p className="text-gray-500">No token found</p>
                    )}
                </div>

                {/* Storage Info */}
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-xl font-bold mb-4">Storage</h2>
                    <div className="space-y-2 text-sm">
                        <p>
                            <span className="font-medium">SessionStorage:</span>{" "}
                            {typeof window !== 'undefined' && sessionStorage.getItem('access_token') ? "✓ Has token" : "✗ No token"}
                        </p>
                        <p>
                            <span className="font-medium">LocalStorage:</span>{" "}
                            {typeof window !== 'undefined' && localStorage.getItem('access_token') ? "✓ Has token" : "✗ No token"}
                        </p>
                    </div>
                </div>

                {/* Actions */}
                <div className="bg-white shadow rounded-lg p-6">
                    <h2 className="text-xl font-bold mb-4">Actions</h2>
                    <div className="space-x-4">
                        <button
                            onClick={logout}
                            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                            Logout (Normal)
                        </button>
                        <button
                            onClick={clearAll}
                            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                        >
                            Clear All Storage
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function DebugPage() {
    return (
        <AuthGuard>
            <DebugContent />
        </AuthGuard>
    );
}
