import { useCallback, useState } from "react";
import { analyzeRisks, getChecklist, simplifyDocument } from "../services/api";
import { useResource } from "../hooks/useResource";
import SummaryTab from "../components/SummaryTab";
import RiskTab from "../components/RiskTab";
import ChatTab from "../components/ChatTab";
import ChecklistTab from "../components/ChecklistTab";

const TABS = [
  { id: "summary", label: "Summary" },
  { id: "risks", label: "Risk Scanner" },
  { id: "chat", label: "Q&A" },
  { id: "checklist", label: "Checklist" },
];

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentPage({ doc, onBack }) {
  const id = doc.document_id;
  const [tab, setTab] = useState("summary");

  // Results and chat live here, so switching tabs never repeats an AI call
  // and never loses the conversation or ticked checklist items.
  const [summary, loadSummary] = useResource(useCallback(() => simplifyDocument(id), [id]));
  const [risks, loadRisks] = useResource(useCallback(() => analyzeRisks(id), [id]));
  const [checklist, loadChecklist] = useResource(useCallback(() => getChecklist(id), [id]));
  const [messages, setMessages] = useState([]);
  const [checked, setChecked] = useState({});

  const meta = [
    doc.extension.slice(1).toUpperCase(),
    formatSize(doc.size_bytes),
    `${doc.word_count.toLocaleString()} words`,
    doc.page_count ? `${doc.page_count} pages` : null,
  ].filter(Boolean).join(" · ");

  return (
    <div className="page">
      <button type="button" className="link-btn" onClick={onBack}>
        ← Upload another document
      </button>

      <header className="doc-header">
        <div className="doc-icon" aria-hidden="true">📄</div>
        <div>
          <h1 className="doc-title">{doc.filename}</h1>
          <p className="hint">{meta}</p>
          {doc.stored_in_s3 && (
            <p className="hint">☁ Original stored in a private AWS S3 bucket</p>
          )}
        </div>
      </header>

      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={`tab ${tab === t.id ? "active" : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <section className="panel" role="tabpanel">
        {tab === "summary" && <SummaryTab resource={summary} load={loadSummary} />}
        {tab === "risks" && <RiskTab resource={risks} load={loadRisks} />}
        {tab === "chat" && (
          <ChatTab documentId={id} messages={messages} setMessages={setMessages} />
        )}
        {tab === "checklist" && (
          <ChecklistTab
            resource={checklist}
            load={loadChecklist}
            checked={checked}
            setChecked={setChecked}
          />
        )}
      </section>
    </div>
  );
}