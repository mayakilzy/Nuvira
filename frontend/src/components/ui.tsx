"use client";
import React from "react";

export function Field({ label, ...props }: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="field">
      <label className="label">{label}</label>
      <input className="input" {...props} />
    </div>
  );
}

export function Alert({ kind, children }: { kind: "error" | "ok"; children: React.ReactNode }) {
  if (!children) return null;
  return <div className={`alert ${kind === "error" ? "alert-error" : "alert-ok"}`}>{children}</div>;
}

export function StatusBadge({ status }: { status: string }) {
  const ok = ["active", "trialing"].includes(status);
  const warn = ["past_due", "cancelled"].includes(status);
  return <span className={`badge ${ok ? "badge-ok" : warn ? "badge-warn" : ""}`}>{status}</span>;
}
