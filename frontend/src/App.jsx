import { useEffect, useState } from "react";
import { checkHealth } from "./services/api";
import UploadPage from "./pages/UploadPage";
import DocumentPage from "./pages/DocumentPage";

function Sidebar({ onHome }) {
  const [online, setOnline] = useState(null); // null = checking

  useEffect(() => {
    checkHealth()
      .then(() => setOnline(true))
      .catch(() => setOnline(false));
  }, []);

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true">C</span>
        <span className="brand-name">ClauseClear</span>
      </div>
      <nav className="side-nav">
        <button type="button" className="nav-item active" onClick={onHome}>
          Home
        </button>
      </nav>
      <div className="side-footer">
        <p>Understand your documents in simple language.</p>
        <p className={`server-status ${online === false ? "off" : ""}`}>
          {online === null ? "Connecting…" : online ? "● Server connected" : "● Server offline"}
        </p>
      </div>
    </aside>
  );
}

export default function App() {
  const [doc, setDoc] = useState(null); // uploaded document info, or null

  return (
    <div className="shell">
      <Sidebar onHome={() => setDoc(null)} />
      <main className="main">
        {doc ? (
          <DocumentPage key={doc.document_id} doc={doc} onBack={() => setDoc(null)} />
        ) : (
          <UploadPage onUploaded={setDoc} />
        )}
      </main>
    </div>
  );
}