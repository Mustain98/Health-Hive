// Token management and auth utilities

const TOKEN_KEY = 'access_token';

/**
 * Save JWT token to sessionStorage (per-tab isolation)
 */
export function setToken(token: string): void {
    if (typeof window !== 'undefined') {
        sessionStorage.setItem(TOKEN_KEY, token);
    }
}

/**
 * Get JWT token from sessionStorage
 */
export function getToken(): string | null {
    if (typeof window !== 'undefined') {
        // Migration: Clean up old localStorage token if it exists
        const oldToken = localStorage.getItem(TOKEN_KEY);
        if (oldToken) {
            localStorage.removeItem(TOKEN_KEY);
        }

        return sessionStorage.getItem(TOKEN_KEY);
    }
    return null;
}

/**
 * Remove JWT token from sessionStorage
 */
export function clearToken(): void {
    if (typeof window !== 'undefined') {
        sessionStorage.removeItem(TOKEN_KEY);
    }
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
    return !!getToken();
}

/**
 * Logout user (clear all storage + redirect)
 */
export function logout(): void {
    if (typeof window !== 'undefined') {
        // Clear from both storages to be thorough
        sessionStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(TOKEN_KEY);

        // Redirect to login
        window.location.href = '/login';
    }
}
