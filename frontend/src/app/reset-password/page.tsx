"use client";
import { Suspense, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Field, Alert } from "@/components/ui";

function ResetInner() {
  const token = useSearchParams().get("token") || "";
  const router = useRouter();
  const [pw, setPw] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setErr(""); setBusy(true);
    try { await api.post("/auth/reset-password", { token, new_password: pw }); router.push("/login"); }
    catch (e: any) { setErr(e?.response?.data?.detail || "Reset link is invalid or expired"); }
    finally { setBusy(false); }
  }
  return (
    <div className="container-narrow card card-pad">
      <h1 style={{ fontSize: 22, marginBottom: 4 }}>Choose a new password</h1>
      <p className="muted" style={{ fontSize: 14, marginBottom: 20 }}>Enter a new password for your account.</p>
      <form onSubmit={submit}>
        <Field label="New password" type="password" value={pw} onChange={(e) => setPw(e.target.value)} required minLength={6} />
        <div style={{ height: 12 }} />
        <Alert kind="error">{err}</Alert>
        <button className="btn btn-primary btn-block" disabled={busy || !token} style={{ marginTop: 12 }}>
          {busy ? "Updating…" : "Update password"}
        </button>
      </form>
    </div>
  );
}
export default function Reset() {
  return (
    <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 20 }}>
      <Suspense><ResetInner /></Suspense>
    </main>
  );
}
