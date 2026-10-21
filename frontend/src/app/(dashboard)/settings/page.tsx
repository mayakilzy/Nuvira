"use client";
import { useEffect, useState } from "react";
import { api, apiError, clearTokens } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Field, Alert } from "@/components/ui";

export default function Settings() {
  const { user, refresh } = useAuth();
  const [name, setName] = useState(""); const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  useEffect(() => { if (user) setName(user.full_name || ""); }, [user]);

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault(); setMsg(""); setErr("");
    try { await api.put("/user/profile", { full_name: name }); await refresh(); setMsg("Profile saved."); }
    catch (e) { setErr(apiError(e)); }
  }
  async function delAccount() {
    if (!confirm("Delete your account permanently? This cannot be undone.")) return;
    try { await api.delete("/user/account"); clearTokens(); window.location.href = "/register"; }
    catch (e) { setErr(apiError(e)); }
  }

  return (
    <>
      <h1 className="page-title">Settings</h1>
      <p className="muted" style={{ marginBottom: 24 }}>Manage your profile and account.</p>

      <div className="card card-pad" style={{ maxWidth: 480 }}>
        <h3 style={{ fontSize: 16, marginBottom: 14 }}>Profile</h3>
        <form onSubmit={saveProfile}>
          <Field label="Full name" value={name} onChange={(e) => setName(e.target.value)} />
          <div className="field"><label className="label">Email</label><input className="input" value={user?.email || ""} disabled /></div>
          <div style={{ height: 12 }} />
          <Alert kind="error">{err}</Alert><Alert kind="ok">{msg}</Alert>
          <button className="btn btn-primary" style={{ marginTop: 12 }}>Save changes</button>
        </form>
      </div>

      <div className="card card-pad" style={{ maxWidth: 480, marginTop: 20, borderColor: "var(--danger-soft)" }}>
        <h3 style={{ fontSize: 16, marginBottom: 6 }}>Delete account</h3>
        <p className="muted" style={{ fontSize: 14, marginBottom: 14 }}>Permanently remove your account and all data.</p>
        <button className="btn btn-danger" onClick={delAccount}>Delete account</button>
      </div>
    </>
  );
}
