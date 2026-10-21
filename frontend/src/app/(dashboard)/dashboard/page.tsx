"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { StatusBadge } from "@/components/ui";

export default function Dashboard() {
  const { user } = useAuth();
  const [balance, setBalance] = useState<number | null>(null);
  const [sub, setSub] = useState<any>(null);
  const [used, setUsed] = useState<number>(0);

  useEffect(() => {
    api.get("/credits/balance").then((r) => setBalance(r.data.balance)).catch(() => {});
    api.get("/billing/subscription").then((r) => setSub(r.data)).catch(() => {});
    api.get("/credits/history").then((r) => {
      const consumed = (r.data as any[]).filter((x) => x.amount < 0).reduce((a, b) => a + Math.abs(b.amount), 0);
      setUsed(consumed);
    }).catch(() => {});
  }, []);

  return (
    <>
      <h1 className="page-title">Overview</h1>
      <p className="muted" style={{ marginBottom: 28 }}>Welcome back{user?.full_name ? `, ${user.full_name}` : ""}.</p>

      {user && !user.is_verified && (
        <div className="alert alert-error" style={{ marginBottom: 20 }}>
          Your email isn’t verified yet. Check your inbox for the verification link.
        </div>
      )}

      <div className="grid-stats">
        <div className="card card-pad">
          <div className="muted" style={{ fontSize: 13 }}>Credits remaining</div>
          <div className="stat-num">{balance ?? "—"}</div>
        </div>
        <div className="card card-pad">
          <div className="muted" style={{ fontSize: 13 }}>Used this period</div>
          <div className="stat-num">{used}</div>
        </div>
        <div className="card card-pad">
          <div className="muted" style={{ fontSize: 13, marginBottom: 8 }}>Subscription</div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 20, fontWeight: 650, textTransform: "capitalize" }}>{sub?.plan ?? "—"}</span>
            {sub && <StatusBadge status={sub.status} />}
          </div>
        </div>
      </div>

      <div className="card card-pad" style={{ marginTop: 24 }}>
        <h3 style={{ fontSize: 16, marginBottom: 6 }}>Your workspace</h3>
        <p className="muted" style={{ fontSize: 14, marginBottom: 16 }}>This is where your product lives. Each project fills it with its own tools.</p>
        <a className="btn btn-primary" href="/workspace">Open workspace</a>
      </div>
    </>
  );
}
