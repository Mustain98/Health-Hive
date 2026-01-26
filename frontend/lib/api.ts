// API wrapper with authentication and error handling
import { getToken } from './auth';

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
      let errorMessage = `HTTP ${response.status}`;
      let errorDetails: any = null;

      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
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
          sessionStorage.removeItem('access_token');
          localStorage.removeItem('access_token');
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
