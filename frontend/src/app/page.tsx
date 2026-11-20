import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function sessionIdForBrowser() {
  const key = "retail-supply-chain-session-id";
  const existing = window.localStorage.getItem(key);
  if (existing && existing.length >= 33) return existing;
  const random = typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const id = `retail-${random}`.padEnd(33, "-");
  window.localStorage.setItem(key, id);
  return id;
}

export default function Page() {
  const [prompt, setPrompt] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => setSessionId(sessionIdForBrowser()), []);

  async function sendPrompt(text: string) {
    if (!text.trim() || text.trim().length === 0) return;
    setLoading(true);
    setAnswer("");
    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: text, sessionId }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Request failed");
      setAnswer(typeof data.response === "string" ? data.response : JSON.stringify(data.response, null, 2));
    } catch (error) {
      setAnswer(`**Error:** ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setLoading(false);
    }
  }

  const isDraft = /requires_human_approval|draft_recommended_order_qty|human approval/i.test(answer);

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: 32, fontFamily: "system-ui" }}>
      <h1>Retail Supply Chain Operations Agent</h1>
      <div style={{ display: "flex", gap: 8 }}>
        <input
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          onKeyDown={(event) => { if (event.key === "Enter") void sendPrompt(prompt); }}
          placeholder="Ask for inventory, history, region status, or a reorder draft"
          style={{ flex: 1, padding: 12 }}
        />
        <button disabled={loading || !sessionId} onClick={() => void sendPrompt(prompt)}>
          {loading ? "Working…" : "Send"}
        </button>
      </div>

      {answer && (
        <article style={{ marginTop: 24, border: "1px solid #ddd", borderRadius: 8, padding: 20 }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer}</ReactMarkdown>
          {isDraft && (
            <div style={{ display: "flex", gap: 12, marginTop: 16 }}>
              <button onClick={() => void sendPrompt("Approve this reorder draft for further review. Record no order and do not execute a purchase.")}>
                Approve Draft
              </button>
              <button onClick={() => void sendPrompt("Reject this reorder draft. Do not execute a purchase.")}>Reject</button>
            </div>
          )}
        </article>
      )}
    </main>
  );
}
