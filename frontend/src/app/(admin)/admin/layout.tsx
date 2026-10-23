"use client";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const path = usePathname();
  useEffect(() => {
    if (!loading && !user) router.push("/login");
    if (!loading && user && user.role !== "admin") router.push("/dashboard");
  }, [loading, user, router]);
  if (loading || !user || user.role !== "admin")
    return <main style={{ display: "grid", placeItems: "center", minHeight: "100vh" }} className="muted">Loading…</main>;
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">Admin</div>
        <a href="/admin/users" className={`nav-link ${path === "/admin/users" ? "active" : ""}`}>Users</a>
        <a href="/admin/curricula" className={`nav-link ${path === "/admin/curricula" ? "active" : ""}`}>Curricula</a>
        <a href="/dashboard" className="nav-link">← Back to app</a>
        <div style={{ marginTop: "auto" }}>
          <button className="nav-link" style={{ width: "100%", textAlign: "left", background: "none", border: 0, cursor: "pointer" }} onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
