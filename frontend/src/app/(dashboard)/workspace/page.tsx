"use client";
/* =========================================================================
   WORKSPACE — per-project UI. Replace this with your product's interface.
   It already has auth, credits and the API client wired up.
   ========================================================================= */
import { useState } from "react";
import { api, apiError } from "@/lib/api";
import { Alert } from "@/components/ui";

export default function Workspace() {
  const [prompt, setPrompt] = useState(""); const [out, setOut] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  async function run() {
    setErr(""); setBusy(true); setOut("");
    try { const r = await api.post("/agent/execute", { prompt }); setOut(r.data.result); }
    catch (e) { setErr(apiError(e)); }
    finally { setBusy(false); }
  }
  return (
    <>
      <h1 className="page-title">Workspace</h1>
      <p className="muted" style={{ marginBottom: 20 }}>Example agent call — swap for your product. Each run consumes credits.</p>
      <div className="card card-pad" style={{ maxWidth: 640 }}>
        <textarea className="input" style={{ height: 120, padding: 12, resize: "vertical" }}
          placeholder="Ask the agent something…" value={prompt} onChange={(e) => setPrompt(e.target.value)} />
        <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
          <button className="btn btn-primary" onClick={run} disabled={busy || !prompt}>{busy ? "Running…" : "Run"}</button>
        </div>
        <div style={{ marginTop: 14 }}><Alert kind="error">{err}</Alert></div>
        {out && <pre style={{ marginTop: 14, whiteSpace: "pre-wrap", fontSize: 14, background: "var(--surface)", padding: 14, borderRadius: 10 }}>{out}</pre>}
      </div>
    </>
  );
}
