// API wrapper with authentication and error handling
import { getToken, setToken, clearToken } from './auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: any;
  headers?: Record<string, string>;
  skipAuth?: boolean;
};

/**
 * Main API fetch wrapper
 * - Attaches JWT token from sessionStorage
 * - Handles JSON serialization
 * - Throws typed errors with status codes
 */
export async function apiFetch<T = any>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = 'GET', body, headers = {}, skipAuth = false } = options;

  // Build headers
  const finalHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...headers,
  };

  if (!skipAuth) {
    const token = getToken();
    if (token) {
      finalHeaders['Authorization'] = `Bearer ${token}`;
    }
  }

  // Build request
  const requestInit: RequestInit = {
    method,
    headers: finalHeaders,
  };

  if (body && method !== 'GET') {
    requestInit.body = JSON.stringify(body);
  }

  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, requestInit);

    // Handle non-OK responses
    if (!response.ok) {
      // If 401, start refresh flow
      if (response.status === 401 && !skipAuth) { // Don't refresh if skipAuth (e.g. login itself)
        try {
          // Attempt to refresh token
          // Note: We use a separate fetch here to avoid infinite loops if apiFetch was used
          const refreshResponse = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            // credentials: 'include' is crucial for sending the HttpOnly cookie
            credentials: 'include',
          });

          if (refreshResponse.ok) {
            const data = await refreshResponse.json();
            const newAccessToken = data.access_token;

            if (newAccessToken) {
              // specific import to avoid circular dependency issues if any, 
              // but here we just need to update storage. 
              // We'll use the imported 'setToken' but we need to ensure imports are correct.
              // Let's assume setToken is available from './auth'
              // (It is imported at top of file)

              setToken(newAccessToken);

              // Retry original request with new token
              const retryHeaders = { ...finalHeaders, 'Authorization': `Bearer ${newAccessToken}` };
              return apiFetch(endpoint, { ...options, headers: retryHeaders });
            }
          }
        } catch (refreshError) {
          console.error("Token refresh failed:", refreshError);
          // Fall through to error throwing -> logout
        }
      }

      let errorMessage = `HTTP ${response.status}`;
      let errorDetails: any = null;

      try {
        const errorData = await response.json();
        if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail.map((d: any) => d.msg).join(", ");
        } else {
          errorMessage = errorData.detail || errorMessage;
        }
        errorDetails = errorData;
      } catch {
        // Response might not be JSON
        errorMessage = await response.text().catch(() => errorMessage);
      }

      throw new ApiError(response.status, errorMessage, errorDetails);
    }

    // Handle empty responses (204, etc.)
    const contentType = response.headers.get('content-type');
    if (!contentType?.includes('application/json')) {
      return {} as T;
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.status === 401) {
        // Clear token and redirect to login
        if (typeof window !== 'undefined') {
          clearToken();

          // We use window.location to force a full refresh and clear React state
          window.location.href = '/login';
        }
      }
      throw error;
    }
    // Network or other errors
    throw new ApiError(0, `Network error: ${(error as Error).message}`);
  }
}

/**
 * Multipart form data upload (for file uploads)
 */
export async function apiUpload<T = any>(
  endpoint: string,
  formData: FormData
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {};

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch { }

      throw new ApiError(response.status, errorMessage);
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(0, `Upload error: ${(error as Error).message}`);
  }
}

/**
 * OAuth2 token login (form-urlencoded)
 */
export async function loginWithGoogle(code: string, redirectUri: string) {
  const response = await fetch(`${API_BASE_URL}/api/auth/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ code, redirect_uri: redirectUri }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(response.status, errorData.detail || 'Google sign-in failed');
  }

  return await response.json();
}

export async function loginWithToken(username: string, password: string) {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);

  const response = await fetch(`${API_BASE_URL}/api/auth/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      errorData.detail || 'Login failed'
    );
  }

  return await response.json();
}
