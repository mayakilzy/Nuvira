"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function Pricing() {
  const [plans, setPlans] = useState<any[]>([]);
  useEffect(() => { api.get("/billing/plans").then((r) => setPlans(r.data)).catch(() => setPlans([])); }, []);
  return (
    <main style={{ maxWidth: 1000, margin: "0 auto", padding: "40px 24px" }}>
      <Link className="muted" href="/" style={{ fontSize: 14 }}>← Home</Link>
      <h1 style={{ fontSize: 36, margin: "16px 0 6px", textAlign: "center" }}>Simple pricing</h1>
      <p className="muted" style={{ textAlign: "center", marginBottom: 36 }}>Start free. Upgrade when you grow.</p>
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${Math.max(plans.length, 1)},1fr)`, gap: 16 }}>
        {plans.map((p) => (
          <div key={p.slug} className="card card-pad">
            <div style={{ fontSize: 16, fontWeight: 650 }}>{p.name}</div>
            <div className="stat-num" style={{ fontSize: 30, margin: "8px 0 2px" }}>
              ${(p.price_monthly / 100).toFixed(0)}<span className="muted" style={{ fontSize: 14, fontWeight: 400 }}>/mo</span>
            </div>
            <div className="muted" style={{ fontSize: 13, marginBottom: 16 }}>{p.credits_per_month} credits / month</div>
            <Link className="btn btn-primary btn-block" href="/register">Get started</Link>
          </div>
        ))}
        {plans.length === 0 && <p className="muted">Pricing loads from the API once plans are seeded.</p>}
      </div>
    </main>
  );
}
