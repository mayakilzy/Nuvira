"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api, setTokens } from "@/lib/api";
import { Field, Alert } from "@/components/ui";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8995";

export default function Login() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);

  // OAuth returns a short-lived, single-use exchange code; bearer tokens never enter the URL.
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const code = p.get("oauth_code");
    if (!code) return;
    window.history.replaceState({}, "", "/login");
    api.post("/auth/oauth/exchange", { code })
      .then((response) => {
        setTokens(response.data);
        router.replace(response.data.return_path || "/dashboard");
      })
      .catch(() => setErr("Google sign-in could not be completed. Please try again."));
  }, [router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setErr(""); setBusy(true);
    try { await login(email, password); router.push("/dashboard"); }
    catch (e: any) { setErr(e?.response?.data?.detail || "Invalid email or password"); }
    finally { setBusy(false); }
  }

  return (
    <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 20 }}>
      <div className="container-narrow card card-pad">
        <h1 style={{ fontSize: 22, marginBottom: 4 }}>Welcome back</h1>
        <p className="muted" style={{ fontSize: 14, marginBottom: 20 }}>Sign in to your account.</p>
        <form onSubmit={submit}>
          <Field label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <Field label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          <div style={{ height: 12 }} />
          <Alert kind="error">{err}</Alert>
          <button className="btn btn-primary btn-block" disabled={busy} style={{ marginTop: 12 }}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <a className="btn btn-ghost btn-block" href={`${API}/auth/google`} style={{ marginTop: 10 }}>Continue with Google</a>
        <div className="hr" />
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
          <a className="muted" href="/forgot-password">Forgot password?</a>
          <a style={{ color: "var(--accent)" }} href="/register">Create account</a>
        </div>
      </div>
    </main>
  );
}
