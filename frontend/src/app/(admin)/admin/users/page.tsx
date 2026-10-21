"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui";

export default function AdminUsers() {
  const [users, setUsers] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    api.get("/admin/users").then((r) => setUsers(r.data)).catch(() => {});
    api.get("/admin/stats").then((r) => setStats(r.data)).catch(() => {});
  }, []);

  const filtered = users.filter((u) => u.email.toLowerCase().includes(q.toLowerCase()));

  return (
    <>
      <h1 className="page-title">Users</h1>
      <p className="muted" style={{ marginBottom: 24 }}>All accounts on your platform.</p>

      <div className="grid-stats" style={{ marginBottom: 24 }}>
        <div className="card card-pad"><div className="muted" style={{ fontSize: 13 }}>Total users</div><div className="stat-num">{stats?.total_users ?? "—"}</div></div>
      </div>

      <div className="card card-pad">
        <input className="input" placeholder="Search by email…" value={q} onChange={(e) => setQ(e.target.value)} style={{ maxWidth: 320, marginBottom: 16 }} />
        <table className="table">
          <thead><tr><th>Email</th><th>Role</th><th>Status</th><th>Joined</th></tr></thead>
          <tbody>
            {filtered.map((u) => (
              <tr key={u.id}>
                <td>{u.email}</td>
                <td style={{ textTransform: "capitalize" }}>{u.role}</td>
                <td><StatusBadge status={u.is_active ? "active" : "disabled"} /></td>
                <td className="muted">{new Date(u.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
            {filtered.length === 0 && <tr><td colSpan={4} className="muted" style={{ textAlign: "center", padding: 24 }}>No users found.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
