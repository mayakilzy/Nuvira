"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { api, setTokens, clearTokens, getTokens } from "./api";

export type User = {
  id: number; email: string; full_name?: string; role: string;
  is_verified: boolean; avatar_url?: string;
};

type Ctx = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, full_name?: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<Ctx>(null as any);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    if (!getTokens()) { setUser(null); setLoading(false); return; }
    try { const r = await api.get("/auth/me"); setUser(r.data); }
    catch { setUser(null); }
    finally { setLoading(false); }
  }
  useEffect(() => { refresh(); }, []);

  async function login(email: string, password: string) {
    const r = await api.post("/auth/login", { email, password });
    setTokens(r.data); await refresh();
  }
  async function register(email: string, password: string, full_name?: string) {
    const r = await api.post("/auth/register", { email, password, full_name });
    setTokens(r.data); await refresh();
  }
  function logout() { clearTokens(); setUser(null); window.location.href = "/login"; }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
