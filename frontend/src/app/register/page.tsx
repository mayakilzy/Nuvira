"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Field, Alert } from "@/components/ui";

export default function Register() {
  const { register } = useAuth();
  const router = useRouter();
  const [name, setName] = useState(""); const [email, setEmail] = useState(""); const [password, setPassword] = useState("");
  const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault(); setErr(""); setBusy(true);
    try { await register(email, password, name); router.push("/dashboard"); }
    catch (e: any) { setErr(e?.response?.data?.detail || "Could not create account"); }
    finally { setBusy(false); }
  }
  return (
    <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 20 }}>
      <div className="container-narrow card card-pad">
        <h1 style={{ fontSize: 22, marginBottom: 4 }}>Create your account</h1>
        <p className="muted" style={{ fontSize: 14, marginBottom: 20 }}>Start in seconds. We’ll email a verification link.</p>
        <form onSubmit={submit}>
          <Field label="Full name" value={name} onChange={(e) => setName(e.target.value)} />
          <Field label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <Field label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} />
          <div style={{ height: 12 }} />
          <Alert kind="error">{err}</Alert>
          <button className="btn btn-primary btn-block" disabled={busy} style={{ marginTop: 12 }}>
            {busy ? "Creating…" : "Create account"}
          </button>
        </form>
        <div className="hr" />
        <p style={{ fontSize: 13 }} className="muted">
          Already have an account? <a style={{ color: "var(--accent)" }} href="/login">Sign in</a>
        </p>
      </div>
    </main>
  );
}
