import { useState } from "react";

const Y = "#f5c518", R = "#e8312a";

const LISTINGS = {
  Brooklyn: [
    { title: "Private Room in Bushwick", price: 760, location: "Bushwick, Brooklyn", description: "Near L train. References required. Standard lease. Meet in person.", safe: true, score: 91, flags: [] },
    { title: "URGENT! Luxury 2BR only $390!!!", price: 390, location: "Williamsburg, Brooklyn", description: "Owner overseas. Send deposit via Western Union NOW. No viewing needed!!!", safe: false, score: 9, flags: ["Price too low", "Wire transfer requested", "Owner overseas", "No viewing allowed", "Urgency tactics"] },
    { title: "Studio in Crown Heights", price: 875, location: "Crown Heights, Brooklyn", description: "Clean studio. Background check required. Weekend viewings available.", safe: true, score: 88, flags: [] },
  ],
  Queens: [
    { title: "Shared Apt in Astoria", price: 820, location: "Astoria, Queens", description: "3BR with 2 roommates. Near N/W train. References needed.", safe: true, score: 85, flags: [] },
    { title: "CHEAP ROOM $350 Queens!!", price: 350, location: "Jamaica, Queens", description: "Send money order upfront. Owner out of country. No visits until paid!!!", safe: false, score: 8, flags: ["Extremely low price", "Money order required", "No viewing", "Owner unavailable"] },
  ],
  Bronx: [
    { title: "Room near Fordham", price: 680, location: "Fordham, Bronx", description: "Near 4/D train. Month-to-month lease. Call to schedule viewing.", safe: true, score: 87, flags: [] },
    { title: "AMAZING DEAL $300 Bronx!!!", price: 300, location: "Bronx", description: "Owner in Europe. Wire deposit via Venmo first. No key until payment. Trust me!!!", safe: false, score: 5, flags: ["Suspiciously low price", "Venmo upfront", "Owner abroad", "No address given"] },
  ],
  Manhattan: [
    { title: "Room in Harlem", price: 950, location: "Harlem, Manhattan", description: "Near A/C train. Standard lease. References and ID required.", safe: true, score: 82, flags: [] },
    { title: "LUXURY APT $420 Manhattan!!!", price: 420, location: "Midtown, Manhattan", description: "Owner overseas. Wire transfer only. No viewing until deposit sent!!!", safe: false, score: 6, flags: ["Impossible price for Manhattan", "Wire transfer only", "Owner overseas", "No viewing"] },
  ],
};

const BUDGETS = ["Under $700", "Under $800", "Under $900", "Under $1000", "Any budget"];
const BOROUGHS = ["Brooklyn", "Queens", "Bronx", "Manhattan"];
const TYPES = ["Any room", "Private room", "Shared room", "Studio"];

export default function App() {
  const [borough, setBorough] = useState(null);
  const [budget, setBudget] = useState(null);
  const [type, setType] = useState(null);
  const [phase, setPhase] = useState("select");
  const [step, setStep] = useState(0);
  const [results, setResults] = useState(null);
  const [detail, setDetail] = useState(null);

  const canSearch = borough && budget && type;

  async function doSearch() {
    setPhase("loading"); setStep(0); setResults(null); setDetail(null);
    for (let i = 1; i <= 5; i++) {
      await new Promise(r => setTimeout(r, i === 4 ? 1000 : 500));
      setStep(i);
    }
    const max = budget === "Any budget" ? 9999 : parseInt(budget.replace(/\D/g, ""));
    const pool = LISTINGS[borough] || [];
    const filtered = pool.filter(l => l.price <= max);
    const final = filtered.length ? filtered : pool.slice(0, 2);
    setResults({ listings: final, safe: final.filter(l => l.safe).length, scams: final.filter(l => !l.safe).length });
    setPhase("results");
  }

  const steps = ["Understanding request", "Fetching listings", "Filtering by budget", "Running scam detection", "Generating report"];

  const s = { fontFamily: "'Syne', sans-serif" };

  if (detail) return (
    <div style={{ maxWidth: 620, margin: "0 auto", padding: "32px 20px 60px", fontFamily: "'DM Sans', sans-serif" }}>
      <button onClick={() => setDetail(null)} style={{ background: "#141414", border: "1px solid rgba(255,255,255,0.07)", color: "#555", padding: "7px 14px", borderRadius: 9, cursor: "pointer", fontSize: 12, marginBottom: 20 }}>← Back</button>
      <div style={{ background: detail.safe ? "rgba(245,197,24,0.04)" : "rgba(232,49,42,0.06)", border: `2px solid ${detail.safe ? "rgba(245,197,24,0.35)" : "rgba(232,49,42,0.4)"}`, borderLeft: `5px solid ${detail.safe ? Y : R}`, borderRadius: 16, padding: 24, position: "relative" }}>
        {!detail.safe && <div style={{ position: "absolute", top: 0, right: 0, background: R, color: "#fff", fontSize: 11, ...s, fontWeight: 700, padding: "5px 16px", borderBottomLeftRadius: 8 }}>🚨 SCAM</div>}
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginBottom: 16 }}>
          <h2 style={{ ...s, fontWeight: 800, fontSize: 18, color: detail.safe ? Y : R, flex: 1 }}>{detail.title}</h2>
          <div style={{ ...s, fontWeight: 800, fontSize: 26, color: detail.safe ? Y : R }}>${detail.price}<span style={{ fontSize: 11, fontWeight: 400, color: "#555" }}>/mo</span></div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 16 }}>
          {[["LOCATION", detail.location], ["CONTACT", "Call or email"], ["SAFETY SCORE", `${detail.score}/100`], ["STATUS", detail.safe ? "LEGITIMATE" : "FRAUDULENT"]].map(([k, v], i) => (
            <div key={i} style={{ background: detail.safe ? "rgba(245,197,24,0.05)" : "rgba(232,49,42,0.07)", border: `1px solid ${detail.safe ? "rgba(245,197,24,0.15)" : "rgba(232,49,42,0.18)"}`, borderRadius: 9, padding: "11px 13px" }}>
              <div style={{ fontSize: 10, color: "#555", marginBottom: 3 }}>{k}</div>
              <div style={{ fontSize: 13, color: k === "SAFETY SCORE" || k === "STATUS" ? (detail.safe ? Y : R) : "#aaa", ...((k === "SAFETY SCORE" || k === "STATUS") ? { ...s, fontWeight: 700, fontSize: 15 } : {}) }}>{v}</div>
            </div>
          ))}
        </div>
        <div style={{ marginBottom: 14 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}><span style={{ fontSize: 11, color: "#555" }}>Safety score</span><span style={{ ...s, fontWeight: 700, color: detail.safe ? Y : R }}>{detail.score}/100</span></div>
          <div style={{ height: 6, background: "rgba(255,255,255,0.06)", borderRadius: 99 }}><div style={{ height: "100%", width: `${detail.score}%`, background: detail.safe ? Y : R, borderRadius: 99 }} /></div>
        </div>
        <div style={{ fontSize: 13, color: "#777", lineHeight: 1.7, background: "rgba(255,255,255,0.02)", borderRadius: 9, padding: 14, marginBottom: 14 }}>{detail.description}</div>
        {detail.flags.length > 0 && (
          <div>
            <div style={{ fontSize: 10, color: R, ...s, fontWeight: 700, letterSpacing: 1, marginBottom: 10 }}>🚨 RED FLAGS</div>
            {detail.flags.map((f, i) => (
              <div key={i} style={{ display: "flex", gap: 10, alignItems: "center", background: "rgba(232,49,42,0.08)", border: "1px solid rgba(232,49,42,0.2)", borderRadius: 8, padding: "8px 13px", marginBottom: 6 }}>
                <span style={{ color: R }}>⚠</span><span style={{ fontSize: 12, color: "#cc7070" }}>{f}</span>
              </div>
            ))}
          </div>
        )}
        {detail.safe && <div style={{ background: "rgba(245,197,24,0.07)", border: "1px solid rgba(245,197,24,0.2)", borderRadius: 9, padding: "13px 15px", fontSize: 13, color: "#999", lineHeight: 1.7 }}>✅ <strong style={{ color: Y }}>Looks legitimate.</strong> Standard lease, in-person viewing, reasonable price. Safe to contact.</div>}
      </div>
    </div>
  );

  return (
    <div style={{ background: "#0d0d0d", minHeight: "100vh", color: "#f0f0f0", fontFamily: "'DM Sans', sans-serif" }}>
      <div style={{ background: "#141414", borderBottom: "1px solid rgba(255,255,255,0.07)", height: 50, display: "flex", alignItems: "center", padding: "0 20px", gap: 8 }}>
        <div style={{ width: 28, height: 28, background: Y, borderRadius: 7, display: "flex", alignItems: "center", justifyContent: "center" }}>🏠</div>
        <span style={{ ...s, fontWeight: 800, fontSize: 16 }}>Safe<span style={{ color: Y }}>Nest</span><span style={{ color: R }}> AI</span></span>
      </div>

      <div style={{ maxWidth: 620, margin: "0 auto", padding: "32px 20px 60px" }}>
        {phase === "select" && (
          <>
            <h2 style={{ ...s, fontWeight: 800, fontSize: 26, letterSpacing: -1, marginBottom: 4 }}>Find Your <span style={{ color: Y }}>Safe</span> Home</h2>
            <p style={{ color: "#555", fontSize: 13, marginBottom: 22 }}>Select your preferences — no typing needed</p>
            <div style={{ background: "#141414", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 16, padding: 24 }}>
              <div style={{ marginBottom: 22 }}>
                <div style={{ fontSize: 10, letterSpacing: 1.5, color: Y, ...s, fontWeight: 700, marginBottom: 12, textTransform: "uppercase" }}>📍 Where in NYC?</div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {BOROUGHS.map(b => <button key={b} onClick={() => setBorough(b)} style={{ padding: "10px 20px", borderRadius: 99, fontSize: 13, cursor: "pointer", transition: "all 0.2s", background: borough === b ? Y : "rgba(245,197,24,0.05)", color: borough === b ? "#0d0d0d" : Y, border: `2px solid ${borough === b ? Y : "rgba(245,197,24,0.18)"}`, fontWeight: borough === b ? 700 : 400 }}>{b}</button>)}
                </div>
              </div>
              <div style={{ borderTop: "1px solid rgba(255,255,255,0.07)", paddingTop: 22, marginBottom: 22, opacity: borough ? 1 : 0.3, transition: "opacity 0.4s" }}>
                <div style={{ fontSize: 10, letterSpacing: 1.5, color: R, ...s, fontWeight: 700, marginBottom: 12, textTransform: "uppercase" }}>💰 Your Budget</div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {BUDGETS.map(b => <button key={b} onClick={() => setBudget(b)} style={{ padding: "10px 20px", borderRadius: 99, fontSize: 13, cursor: "pointer", transition: "all 0.2s", background: budget === b ? R : "rgba(232,49,42,0.05)", color: budget === b ? "#fff" : R, border: `2px solid ${budget === b ? R : "rgba(232,49,42,0.18)"}`, fontWeight: budget === b ? 700 : 400 }}>{b}</button>)}
                </div>
              </div>
              <div style={{ borderTop: "1px solid rgba(255,255,255,0.07)", paddingTop: 22, opacity: budget ? 1 : 0.3, transition: "opacity 0.4s" }}>
                <div style={{ fontSize: 10, letterSpacing: 1.5, color: "#666", ...s, fontWeight: 700, marginBottom: 12, textTransform: "uppercase" }}>🏠 Room Type</div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {TYPES.map(t => <button key={t} onClick={() => setType(t)} style={{ padding: "10px 20px", borderRadius: 99, fontSize: 13, cursor: "pointer", transition: "all 0.2s", background: type === t ? "#333" : "rgba(255,255,255,0.03)", color: type === t ? "#fff" : "#555", border: `2px solid ${type === t ? "#555" : "rgba(255,255,255,0.07)"}` }}>{t}</button>)}
                </div>
              </div>
            </div>
            {canSearch && <div style={{ background: "rgba(245,197,24,0.06)", border: "1px solid rgba(245,197,24,0.2)", borderRadius: 10, padding: "11px 16px", marginTop: 14, fontSize: 13, color: "#888" }}>Searching: <strong style={{ color: Y }}>{type}</strong> in <strong style={{ color: Y }}>{borough}</strong> · <strong style={{ color: R }}>{budget}</strong></div>}
            <button onClick={doSearch} disabled={!canSearch} style={{ width: "100%", padding: 15, borderRadius: 13, border: "none", marginTop: 14, background: canSearch ? `linear-gradient(135deg,${Y},${R})` : "rgba(255,255,255,0.04)", color: canSearch ? "#0d0d0d" : "#333", ...s, fontWeight: 800, fontSize: 14, cursor: canSearch ? "pointer" : "not-allowed" }}>
              {canSearch ? "Find Safe Housing →" : "Select all options above"}
            </button>
          </>
        )}

        {phase === "loading" && (
          <div style={{ textAlign: "center", paddingTop: 60 }}>
            <div style={{ width: 48, height: 48, border: "3px solid rgba(255,255,255,0.06)", borderTopColor: Y, borderRadius: "50%", animation: "spin 0.7s linear infinite", margin: "0 auto 20px" }} />
            <h2 style={{ ...s, fontWeight: 800, fontSize: 20, marginBottom: 6 }}>Analyzing <span style={{ color: Y }}>{borough}</span>...</h2>
            <p style={{ color: "#444", fontSize: 13, marginBottom: 28 }}>AI reading every listing for red flags</p>
            <div style={{ maxWidth: 380, margin: "0 auto", textAlign: "left" }}>
              {steps.map((lbl, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "11px 15px", background: step > i ? "rgba(245,197,24,0.06)" : step === i ? "rgba(232,49,42,0.07)" : "rgba(255,255,255,0.02)", border: `1px solid ${step > i ? "rgba(245,197,24,0.25)" : step === i ? "rgba(232,49,42,0.3)" : "rgba(255,255,255,0.07)"}`, borderRadius: 10, marginBottom: 7, transition: "all 0.4s" }}>
                  <div style={{ width: 22, height: 22, borderRadius: "50%", border: `1.5px solid ${step > i ? Y : step === i ? R : "rgba(255,255,255,0.07)"}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, color: step > i ? Y : step === i ? R : "#333", flexShrink: 0, ...s, fontWeight: 700 }}>{step > i ? "✓" : step === i ? "●" : i + 1}</div>
                  <div style={{ fontSize: 13, color: step > i ? Y : step === i ? R : "#333", fontWeight: step === i ? 500 : 400 }}>{lbl}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {phase === "results" && results && (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18 }}>
              <div><h2 style={{ ...s, fontWeight: 800, fontSize: 20, marginBottom: 3 }}>Results — <span style={{ color: Y }}>{borough}</span></h2><div style={{ fontSize: 12, color: "#444" }}>{budget} · {type}</div></div>
              <button onClick={() => { setPhase("select"); setResults(null); }} style={{ background: "#141414", border: "1px solid rgba(255,255,255,0.07)", color: "#555", padding: "7px 14px", borderRadius: 9, cursor: "pointer", fontSize: 12 }}>← New Search</button>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 8, marginBottom: 20 }}>
              {[{ n: results.safe, l: "Safe", c: Y, bg: "rgba(245,197,24,0.07)", bc: "rgba(245,197,24,0.2)" }, { n: results.scams, l: "Scams", c: R, bg: "rgba(232,49,42,0.07)", bc: "rgba(232,49,42,0.2)" }, { n: results.listings.length, l: "Total", c: "#ddd", bg: "rgba(255,255,255,0.03)", bc: "rgba(255,255,255,0.07)" }].map((st, i) => (
                <div key={i} style={{ background: st.bg, border: `1px solid ${st.bc}`, borderRadius: 11, padding: 14, textAlign: "center" }}>
                  <div style={{ ...s, fontWeight: 800, fontSize: 28, color: st.c }}>{st.n}</div>
                  <div style={{ fontSize: 11, color: "#444", marginTop: 2 }}>{st.l}</div>
                </div>
              ))}
            </div>
            {results.listings.map((l, i) => (
              <div key={i} onClick={() => setDetail(l)} style={{ background: l.safe ? "rgba(245,197,24,0.025)" : "rgba(232,49,42,0.07)", border: `1.5px solid ${l.safe ? "rgba(245,197,24,0.15)" : "rgba(232,49,42,0.4)"}`, borderLeft: `4px solid ${l.safe ? Y : R}`, borderRadius: 13, padding: "15px 18px", marginBottom: 9, cursor: "pointer", position: "relative", overflow: "hidden" }}>
                {!l.safe && <div style={{ position: "absolute", top: 0, right: 0, background: R, color: "#fff", fontSize: 10, ...s, fontWeight: 700, padding: "3px 12px", borderBottomLeftRadius: 7 }}>SCAM</div>}
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10, marginBottom: 5 }}>
                  <div style={{ ...s, fontWeight: 700, fontSize: 14, flex: 1, color: l.safe ? "#f0f0f0" : R }}>{l.title}</div>
                  <div style={{ ...s, fontWeight: 800, fontSize: 19, color: l.safe ? Y : R }}>${l.price}<span style={{ fontSize: 11, fontWeight: 400, color: "#444" }}>/mo</span></div>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <div style={{ fontSize: 12, color: "#444" }}>📍 {l.location}</div>
                  <div style={{ ...s, fontWeight: 700, fontSize: 13, color: l.score > 70 ? Y : R }}>{l.score}/100</div>
                </div>
                <div style={{ fontSize: 11, color: "#333", marginTop: 5 }}>Tap for full AI analysis →</div>
              </div>
            ))}
          </>
        )}
      </div>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}*{box-sizing:border-box}`}</style>
    </div>
  );
}