"use client";
import React, { useId } from "react";

export function Field({ label, ...props }: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  const generatedId = useId();
  const inputId = props.id || generatedId;
  return (
    <div className="field">
      <label className="label" htmlFor={inputId}>{label}</label>
      <input className="input" {...props} id={inputId} />
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
