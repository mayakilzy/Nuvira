"use client";
import { useEffect, useState } from "react";
import { api, apiError } from "@/lib/api";
import { StatusBadge, Alert } from "@/components/ui";

export default function Billing() {
  const [sub, setSub] = useState<any>(null);
  const [plans, setPlans] = useState<any[]>([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    api.get("/billing/subscription").then((r) => setSub(r.data)).catch(() => {});
    // public plans endpoint; falls back gracefully if not present yet
    api.get("/billing/plans").then((r) => setPlans(r.data)).catch(() => setPlans([]));
  }, []);

  async function upgrade(slug: string) {
    setErr(""); setBusy(slug);
    try {
      const r = await api.post("/billing/create-checkout-session", { plan_slug: slug, interval: "monthly" });
      window.location.href = r.data.url;
    } catch (e) { setErr(apiError(e)); setBusy(""); }
  }
  async function manage() {
    setErr(""); setBusy("portal");
    try { const r = await api.post("/billing/create-portal-session"); window.location.href = r.data.url; }
    catch (e) { setErr(apiError(e)); setBusy(""); }
  }

  return (
    <>
      <h1 className="page-title">Billing</h1>
      <p className="muted" style={{ marginBottom: 24 }}>Manage your plan and credits.</p>
      <Alert kind="error">{err}</Alert>

      <div className="card card-pad" style={{ marginTop: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div className="muted" style={{ fontSize: 13 }}>Current plan</div>
            <div style={{ fontSize: 22, fontWeight: 650, textTransform: "capitalize" }}>{sub?.plan ?? "free"}</div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            {sub && <StatusBadge status={sub.status} />}
            <button className="btn btn-ghost" onClick={manage} disabled={busy === "portal"}>Manage subscription</button>
          </div>
        </div>
      </div>

      <h3 style={{ fontSize: 16, margin: "28px 0 14px" }}>Plans</h3>
      <div className="grid-stats">
        {plans.length === 0 && <p className="muted" style={{ fontSize: 14 }}>Add a public <code>/billing/plans</code> endpoint or seed plans to list them here.</p>}
        {plans.map((p) => (
          <div key={p.slug} className="card card-pad">
            <div style={{ fontSize: 16, fontWeight: 650 }}>{p.name}</div>
            <div className="stat-num" style={{ fontSize: 26 }}>
              ${(p.price_monthly / 100).toFixed(0)}<span className="muted" style={{ fontSize: 13, fontWeight: 400 }}>/mo</span>
            </div>
            <div className="muted" style={{ fontSize: 13, margin: "4px 0 14px" }}>{p.credits_per_month} credits / month</div>
            <button className="btn btn-primary btn-block" disabled={busy === p.slug || sub?.plan === p.slug}
              onClick={() => upgrade(p.slug)}>
              {sub?.plan === p.slug ? "Current plan" : busy === p.slug ? "Redirecting…" : "Choose plan"}
            </button>
          </div>
        ))}
      </div>
    </>
  );
}
