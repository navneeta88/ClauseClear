import { useEffect, useRef, useState } from "react";
import { askQuestion } from "../services/api";
import { Disclaimer } from "./Status";

const SUGGESTIONS = [
  "When does this contract expire?",
  "How can this agreement be ended, and how much notice is needed?",
  "What payments does this document require?",
  "What happens if a payment is late?",
];

export default function ChatTab({ documentId, messages, setMessages }) {
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const listRef = useRef(null);

  // Keep the newest message in view (scrolls the chat box, not the whole page).
  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, busy]);

  async function send(text) {
    const question = text.trim();
    if (!question || busy) return;

    // Earlier turns help the AI understand follow-ups like "and the landlord?".
    const history = messages
      .filter((m) => !m.error)
      .map((m) => ({ role: m.role, content: m.text }));

    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setInput("");
    setBusy(true);
    try {
      const r = await askQuestion(documentId, question, history);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: r.answer, sources: r.sources, answered: r.answered },
      ]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", text: err.message, error: true }]);
    } finally {
      setBusy(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    send(input);
  }

  return (
    <div className="chat">
      <h2>Ask ClauseClear</h2>
      <div className="chat-list" ref={listRef} aria-live="polite">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>Ask anything about this document. Answers come only from the document.</p>
            <div className="chips">
              {SUGGESTIONS.map((s) => (
                <button key={s} type="button" className="chip" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => {
          const cls = [
            "msg",
            m.role,
            m.error ? "error" : "",
            m.role === "assistant" && m.answered === false ? "unanswered" : "",
          ].join(" ");
          return (
            <div key={i} className={cls}>
              <p>{m.text}</p>
              {m.sources && m.sources.length > 0 && (
                <details className="src">
                  <summary>
                    Source: {[...new Set(m.sources.map((s) => s.section))].join(", ")}
                  </summary>
                  {m.sources.map((s, j) => (
                    <blockquote key={j}>
                      <strong>{s.section}:</strong> {s.quote}
                    </blockquote>
                  ))}
                </details>
              )}
            </div>
          );
        })}

        {busy && <div className="msg assistant typing">Reading the document…</div>}
      </div>

      <form className="chat-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          maxLength={500}
          disabled={busy}
          placeholder="Ask a question about this document…"
          aria-label="Your question"
          onChange={(e) => setInput(e.target.value)}
        />
        <button type="submit" className="btn" disabled={busy || !input.trim()}>
          Send
        </button>
      </form>

      <p className="hint">
        Only answers based on the uploaded document. If the information isn't in it,
        ClauseClear will say so.
      </p>
      <Disclaimer />
    </div>
  );
}
