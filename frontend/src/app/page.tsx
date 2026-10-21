import Link from "next/link";

export default function Landing() {
  return (
    <main>
      <nav style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "20px 28px", maxWidth: 1080, margin: "0 auto" }}>
        <div style={{ fontWeight: 700, letterSpacing: "-.02em" }}>SaaS Template</div>
        <div style={{ display: "flex", gap: 10 }}>
          <Link className="btn btn-ghost" href="/pricing">Pricing</Link>
          <Link className="btn btn-ghost" href="/login">Sign in</Link>
          <Link className="btn btn-primary" href="/register">Get started</Link>
        </div>
      </nav>

      <section style={{ maxWidth: 760, margin: "0 auto", padding: "80px 24px 40px", textAlign: "center" }}>
        <span className="badge" style={{ marginBottom: 20 }}>Production-ready starter</span>
        <h1 style={{ fontSize: 48, lineHeight: 1.05, margin: "0 0 18px" }}>Ship your SaaS in days, not months.</h1>
        <p className="muted" style={{ fontSize: 18, maxWidth: 560, margin: "0 auto 28px" }}>
          Auth, billing, credits, and an AI layer are already built and tested. Bring your idea — the plumbing is done.
        </p>
        <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
          <Link className="btn btn-primary" href="/register">Start free</Link>
          <Link className="btn btn-ghost" href="/pricing">See pricing</Link>
        </div>
      </section>

      <section style={{ maxWidth: 1000, margin: "0 auto", padding: "20px 24px 80px", display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 16 }}>
        {[
          ["Auth & accounts", "Email, Google sign-in, verification and password reset out of the box."],
          ["Payments & credits", "Lemon Squeezy, Paddle or Stripe with a metered credit ledger."],
          ["AI built in", "Model-agnostic via OpenRouter — wire your agent and go."],
        ].map(([t, d]) => (
          <div key={t} className="card card-pad">
            <h3 style={{ fontSize: 16, marginBottom: 8 }}>{t}</h3>
            <p className="muted" style={{ fontSize: 14 }}>{d}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
