import UploadBox from "../components/UploadBox";

const FEATURES = [
  { icon: "📄", title: "Simple Summary", text: "Legal language, simplified" },
  { icon: "🛡️", title: "Risk Scanner", text: "Spot important clauses" },
  { icon: "💬", title: "Ask Questions", text: "Answers only from your document" },
  { icon: "✅", title: "Checklist", text: "Action items and key dates" },
];

export default function UploadPage({ onUploaded }) {
  return (
    <div className="page">
      <section className="hero">
        <h1>ClauseClear</h1>
        <p className="hero-sub">Understand your legal documents in simple language.</p>
        <p className="hero-text">
          Upload a PDF or DOCX and get a plain-English summary, important clauses
          flagged, a checklist, and answers grounded in your document.
        </p>
      </section>

      <UploadBox onUploaded={onUploaded} />
      <p className="hint center">Supported: text-based PDF or DOCX, up to 10 MB (scanned images are not supported)</p>

      <div className="feature-grid">
        {FEATURES.map((f) => (
          <div className="feature" key={f.title}>
            <div className="feature-icon" aria-hidden="true">{f.icon}</div>
            <strong>{f.title}</strong>
            <p className="hint">{f.text}</p>
          </div>
        ))}
      </div>

      <p className="hint center">
        Your document text is sent to an AI service (Groq) to produce these results.
        Don't upload documents you aren't comfortable sharing. ClauseClear is an
        information tool, not a lawyer.
      </p>
    </div>
  );
}