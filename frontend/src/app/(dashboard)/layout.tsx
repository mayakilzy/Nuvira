"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => { if (!loading && !user) router.push("/login"); }, [loading, user, router]);
  if (loading || !user) return <main style={{ display: "grid", placeItems: "center", minHeight: "100vh" }} className="muted">Loading…</main>;

  return <>{children}</>;
}
