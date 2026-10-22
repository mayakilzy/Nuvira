import axios from "axios";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8995";
export const api = axios.create({ baseURL: BASE, withCredentials: true });

const ACCESS_KEY = "nuvira_access_token";
const LEGACY_KEY = "saas_tokens";
type AccessToken = { access_token: string };

export function getTokens(): AccessToken | null {
  if (typeof window === "undefined") return null;
  const current = sessionStorage.getItem(ACCESS_KEY);
  if (current) return { access_token: current };
  // One-way cleanup: never retain the legacy long-lived refresh token.
  const legacy = localStorage.getItem(LEGACY_KEY);
  if (legacy) {
    try {
      const parsed = JSON.parse(legacy) as AccessToken;
      if (parsed.access_token) sessionStorage.setItem(ACCESS_KEY, parsed.access_token);
    } finally {
      localStorage.removeItem(LEGACY_KEY);
    }
  }
  const migrated = sessionStorage.getItem(ACCESS_KEY);
  return migrated ? { access_token: migrated } : null;
}

export function setTokens(value: AccessToken) {
  sessionStorage.setItem(ACCESS_KEY, value.access_token);
  localStorage.removeItem(LEGACY_KEY);
}

export function clearTokens() {
  sessionStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(LEGACY_KEY);
}

api.interceptors.request.use((config) => {
  const token = getTokens();
  if (token?.access_token) config.headers.Authorization = `Bearer ${token.access_token}`;
  return config;
});

let refreshing: Promise<string | null> | null = null;
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const isSessionEndpoint = String(original?.url || "").startsWith("/auth/refresh");
    if (error.response?.status === 401 && !isSessionEndpoint && !original?._retried) {
      original._retried = true;
      if (!refreshing) {
        refreshing = axios.post(`${BASE}/auth/refresh`, {}, { withCredentials: true })
          .then((response) => {
            setTokens(response.data);
            return response.data.access_token as string;
          })
          .catch(() => {
            clearTokens();
            return null;
          })
          .finally(() => { refreshing = null; });
      }
      const newToken = await refreshing;
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      }
    }
    return Promise.reject(error);
  },
);

export function apiError(error: any): string {
  return error?.response?.data?.detail || error?.message || "Something went wrong";
}
