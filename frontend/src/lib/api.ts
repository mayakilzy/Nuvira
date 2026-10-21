import axios from "axios";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8995";
export const api = axios.create({ baseURL: BASE });

const KEY = "saas_tokens";
type Tokens = { access_token: string; refresh_token: string };

export function getTokens(): Tokens | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(KEY);
  return raw ? (JSON.parse(raw) as Tokens) : null;
}
export function setTokens(t: Tokens) { localStorage.setItem(KEY, JSON.stringify(t)); }
export function clearTokens() { localStorage.removeItem(KEY); }

api.interceptors.request.use((config) => {
  const t = getTokens();
  if (t?.access_token) config.headers.Authorization = `Bearer ${t.access_token}`;
  return config;
});

// On 401, try a one-time refresh, then retry the original request.
let refreshing: Promise<string | null> | null = null;
api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    const t = getTokens();
    if (error.response?.status === 401 && t?.refresh_token && !original._retried) {
      original._retried = true;
      if (!refreshing) {
        refreshing = axios
          .post(`${BASE}/auth/refresh`, { refresh_token: t.refresh_token })
          .then((res) => { setTokens(res.data); return res.data.access_token as string; })
          .catch(() => { clearTokens(); return null; })
          .finally(() => { refreshing = null; });
      }
      const newToken = await refreshing;
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      }
    }
    return Promise.reject(error);
  }
);

export function apiError(e: any): string {
  return e?.response?.data?.detail || e?.message || "Something went wrong";
}
