"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { Field, Alert } from "@/components/ui";

export default function Forgot() {
  const [email, setEmail] = useState(""); const [done, setDone] = useState(false); const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true);
    try { await api.post("/auth/forgot-password", { email }); } finally { setDone(true); setBusy(false); }
  }
  return (
    <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 20 }}>
      <div className="container-narrow card card-pad">
        <h1 style={{ fontSize: 22, marginBottom: 4 }}>Reset password</h1>
        <p className="muted" style={{ fontSize: 14, marginBottom: 20 }}>Enter your email and we’ll send a reset link.</p>
        {done ? (
          <Alert kind="ok">If that email exists, a reset link is on its way.</Alert>
        ) : (
          <form onSubmit={submit}>
            <Field label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            <button className="btn btn-primary btn-block" disabled={busy} style={{ marginTop: 14 }}>
              {busy ? "Sending…" : "Send reset link"}
            </button>
          </form>
        )}
        <div className="hr" />
        <a style={{ fontSize: 13, color: "var(--accent)" }} href="/login">Back to sign in</a>
      </div>
    </main>
  );
}
