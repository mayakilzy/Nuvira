"use client";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

function VerifyInner() {
  const token = useSearchParams().get("token") || "";
  const [state, setState] = useState<"loading" | "ok" | "error">("loading");
  useEffect(() => {
    if (!token) { setState("error"); return; }
    api.get(`/auth/verify-email/${token}`).then(() => setState("ok")).catch(() => setState("error"));
  }, [token]);
  return (
    <div className="container-narrow card card-pad" style={{ textAlign: "center" }}>
      {state === "loading" && <p className="muted">Verifying your email…</p>}
      {state === "ok" && (<>
        <h1 style={{ fontSize: 22, marginBottom: 8 }}>Email verified</h1>
        <p className="muted" style={{ fontSize: 14, marginBottom: 18 }}>Your account is ready.</p>
        <a className="btn btn-primary btn-block" href="/dashboard">Go to dashboard</a>
      </>)}
      {state === "error" && (<>
        <h1 style={{ fontSize: 22, marginBottom: 8 }}>Link expired</h1>
        <p className="muted" style={{ fontSize: 14, marginBottom: 18 }}>This verification link is invalid or has expired.</p>
        <a className="btn btn-ghost btn-block" href="/dashboard">Continue</a>
      </>)}
    </div>
  );
}
export default function Verify() {
  return (
    <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 20 }}>
      <Suspense><VerifyInner /></Suspense>
    </main>
  );
}
