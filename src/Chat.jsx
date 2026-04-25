import { useState, useRef, useEffect } from "react";

const Y = "#f5c518", R = "#e8312a";
const API = "http://localhost:8000";

const SUGGESTIONS = [
  "Find 1BR in Brooklyn under $1,400",
  "Is this listing a scam?",
  "I earn $4,000/mo, what can I afford?",
  "What are tenant rights in NYC?",
];

export default function Chat() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: "bot", text: "Hi! I'm SafeNest AI 👋\n\nI can help you find safe housing, detect scams, and calculate affordability. What are you looking for?" }
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [toolLabel, setToolLabel] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, toolLabel]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  }

  function pickSuggestion(text) {
    setShowSuggestions(false);
    setInput(text);
    sendText(text);
  }

  function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setShowSuggestions(false);
    sendText(text);
  }

  async function sendText(text) {
    setBusy(true);
    setMessages(prev => [...prev, { role: "user", text }]);
    const newHistory = [...history, { role: "user", content: text }];
    setHistory(newHistory);
    setToolLabel(null);

    try {
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: newHistory }),
      });

      if (!res.ok) throw new Error(`Server error ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let botText = "";
      let botIndex = null;

      const flush = (t) => {
        if (botIndex === null) {
          setMessages(prev => { botIndex = prev.length; return [...prev, { role: "bot", text: t }]; });
        } else {
          setMessages(prev => prev.map((m, i) => i === botIndex ? { ...m, text: t } : m));
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          const data = JSON.parse(line.slice(6));
          if (data.type === "text") {
            botText += data.content;
            flush(botText);
          } else if (data.type === "tool_call") {
            const labels = { search_listings: "🔍 Searching listings...", calculate_affordability: "📊 Calculating..." };
            setToolLabel(labels[data.name] || "⚙️ Working...");
          } else if (data.type === "done") {
            setToolLabel(null);
          }
        }
      }

      if (botText) setHistory(prev => [...prev, { role: "assistant", content: botText }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: "bot", text: `Sorry, something went wrong: ${err.message}` }]);
    }

    setBusy(false);
  }

  function fmt(text) {
    return text
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br/>");
  }

  const s = { fontFamily: "'Syne', sans-serif" };

  return (
    <>
      {/* FAB */}
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          position: "fixed", bottom: 24, right: 24,
          width: 56, height: 56, borderRadius: "50%",
          background: `linear-gradient(135deg, ${Y}, ${R})`,
          border: "none", cursor: "pointer",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 22, boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
          zIndex: 1000, transition: "transform 0.2s",
        }}
        onMouseEnter={e => e.currentTarget.style.transform = "scale(1.08)"}
        onMouseLeave={e => e.currentTarget.style.transform = "scale(1)"}
        title="Chat with SafeNest AI"
      >
        {open ? "✕" : "💬"}
      </button>

      {/* Panel */}
      {open && (
        <div style={{
          position: "fixed", bottom: 90, right: 24,
          width: 360, height: 520,
          background: "#141414", border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 18, display: "flex", flexDirection: "column",
          boxShadow: "0 20px 60px rgba(0,0,0,0.7)", zIndex: 999,
          overflow: "hidden",
          animation: "slideUp 0.2s ease-out",
        }}>
          {/* Header */}
          <div style={{ background: "#1a1a1a", borderBottom: "1px solid rgba(255,255,255,0.07)", padding: "14px 18px", display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
            <div style={{ width: 32, height: 32, background: Y, borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, flexShrink: 0 }}>🏠</div>
            <div>
              <div style={{ ...s, fontWeight: 800, fontSize: 14, color: "#f0f0f0" }}>Safe<span style={{ color: Y }}>Nest</span><span style={{ color: R }}> AI</span></div>
              <div style={{ fontSize: 10, color: "#444" }}>Housing Assistant · Always on</div>
            </div>
          </div>

          {/* Messages */}
          <div style={{ flex: 1, overflowY: "auto", padding: "14px", display: "flex", flexDirection: "column", gap: 10, scrollBehavior: "smooth" }}>
            {messages.map((m, i) => (
              <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
                <div style={{
                  maxWidth: "82%", padding: "10px 13px", borderRadius: 12, fontSize: 13, lineHeight: 1.55,
                  background: m.role === "user"
                    ? `linear-gradient(135deg, ${Y}22, ${R}22)`
                    : "rgba(255,255,255,0.04)",
                  border: m.role === "user"
                    ? `1px solid ${Y}44`
                    : "1px solid rgba(255,255,255,0.07)",
                  color: m.role === "user" ? "#f0f0f0" : "#aaa",
                  borderBottomRightRadius: m.role === "user" ? 3 : 12,
                  borderBottomLeftRadius: m.role === "bot" ? 3 : 12,
                }}
                  dangerouslySetInnerHTML={{ __html: fmt(m.text) }}
                />
              </div>
            ))}

            {toolLabel && (
              <div style={{ display: "flex", justifyContent: "flex-start" }}>
                <div style={{ padding: "7px 12px", background: "rgba(245,197,24,0.07)", border: "1px solid rgba(245,197,24,0.15)", borderRadius: 20, fontSize: 11, color: Y }}>
                  {toolLabel}
                </div>
              </div>
            )}

            {busy && !toolLabel && (
              <div style={{ display: "flex", justifyContent: "flex-start" }}>
                <div style={{ padding: "10px 14px", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 12, borderBottomLeftRadius: 3, display: "flex", gap: 5, alignItems: "center" }}>
                  {[0, 0.15, 0.3].map((delay, i) => (
                    <span key={i} style={{ width: 6, height: 6, background: "#444", borderRadius: "50%", display: "inline-block", animation: `bounce 0.9s ${delay}s infinite` }} />
                  ))}
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Suggestions */}
          {showSuggestions && !busy && (
            <div style={{ padding: "8px 12px 0", display: "flex", gap: 6, overflowX: "auto", flexShrink: 0 }}>
              {SUGGESTIONS.map((s, i) => (
                <button key={i} onClick={() => pickSuggestion(s)} style={{
                  padding: "5px 11px", borderRadius: 99, border: `1px solid ${Y}33`,
                  background: `${Y}0d`, color: Y, fontSize: 11, cursor: "pointer", whiteSpace: "nowrap",
                  fontFamily: "inherit",
                }}>
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div style={{ padding: "10px 12px", borderTop: "1px solid rgba(255,255,255,0.06)", display: "flex", gap: 8, alignItems: "center", flexShrink: 0 }}>
            <input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask about NYC housing..."
              disabled={busy}
              style={{
                flex: 1, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 20, padding: "9px 14px", fontSize: 13, color: "#f0f0f0",
                outline: "none", fontFamily: "inherit",
              }}
            />
            <button
              onClick={send}
              disabled={busy || !input.trim()}
              style={{
                width: 36, height: 36, borderRadius: "50%", border: "none", cursor: busy ? "not-allowed" : "pointer",
                background: input.trim() && !busy ? `linear-gradient(135deg,${Y},${R})` : "rgba(255,255,255,0.06)",
                display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                transition: "all 0.2s",
              }}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke={input.trim() && !busy ? "#0d0d0d" : "#333"} strokeWidth="2.5">
                <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </div>
      )}

      <style>{`
        @keyframes slideUp { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes bounce { 0%,60%,100% { transform: translateY(0); } 30% { transform: translateY(-5px); } }
      `}</style>
    </>
  );
}
