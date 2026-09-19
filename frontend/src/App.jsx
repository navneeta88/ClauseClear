import { useEffect, useState } from "react";
import { checkHealth } from "./services/api";
import UploadBox from "./components/UploadBox";

function formatSize(bytes) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function App() {
  const [status, setStatus] = useState("checking"); // "checking" | "ok" | "error"
  const [doc, setDoc] = useState(null); // uploaded document info, or null

  useEffect(() => {
    checkHealth()
      .then(() => setStatus("ok"))
      .catch(() => setStatus("error"));
  }, []);

  return (
    <div className="app">
      <h1>ClauseClear</h1>
      <p className="tagline">Understand your documents in simple language.</p>

      <p className="status">
        {status === "checking" && "Connecting to the server…"}
        {status === "ok" && "✅ Backend connected"}
        {status === "error" && "❌ Cannot reach the server. Is Flask running on port 5000?"}
      </p>

      {doc ? (
        <div className="doc-card">
          <p><strong>Document:</strong> {doc.filename}</p>
          <p className="hint">
            {formatSize(doc.size_bytes)} · {doc.word_count} words
            {doc.page_count ? ` · ${doc.page_count} pages` : ""}
          </p>
          <p><strong>Extracted text preview</strong></p>
          <pre className="preview">{doc.preview}</pre>
          <button type="button" className="btn secondary" onClick={() => setDoc(null)}>
            Upload another
          </button>
        </div>
      ) : (
        <UploadBox onUploaded={setDoc} />
      )}
    </div>
  );
}