"use client";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

const NAV = [
  { href: "/dashboard", label: "Overview" },
  { href: "/workspace", label: "Workspace" },
  { href: "/billing", label: "Billing" },
  { href: "/settings", label: "Settings" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const path = usePathname();

  useEffect(() => { if (!loading && !user) router.push("/login"); }, [loading, user, router]);
  if (loading || !user) return <main style={{ display: "grid", placeItems: "center", minHeight: "100vh" }} className="muted">Loading…</main>;

  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">SaaS Template</div>
        {NAV.map((n) => (
          <a key={n.href} href={n.href} className={`nav-link ${path === n.href ? "active" : ""}`}>{n.label}</a>
        ))}
        {user.role === "admin" && (
          <a href="/admin/users" className={`nav-link ${path.startsWith("/admin") ? "active" : ""}`}>Admin</a>
        )}
        <div style={{ marginTop: "auto", paddingTop: 16 }}>
          <div className="muted" style={{ fontSize: 12, padding: "0 10px 8px" }}>{user.email}</div>
          <button className="nav-link" style={{ width: "100%", textAlign: "left", background: "none", border: 0, cursor: "pointer" }} onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
