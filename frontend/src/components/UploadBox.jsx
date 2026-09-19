import { useRef, useState } from "react";
import { uploadDocument } from "../services/api";

const MAX_MB = 10;
const ALLOWED = [".pdf", ".docx"];

// Returns an error message, or null if the file is fine.
function validate(file) {
  const name = file.name.toLowerCase();
  if (!ALLOWED.some((ext) => name.endsWith(ext))) {
    return "Only PDF and DOCX files are supported.";
  }
  if (file.size === 0) return "This file is empty.";
  if (file.size > MAX_MB * 1024 * 1024) {
    return `File is too large. Maximum size is ${MAX_MB} MB.`;
  }
  return null;
}

export default function UploadBox({ onUploaded }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState(null); // null = not uploading
  const [error, setError] = useState("");

  async function handleFile(file) {
    setError("");
    const problem = validate(file);
    if (problem) {
      setError(problem);
      return;
    }
    try {
      setProgress(0);
      const doc = await uploadDocument(file, setProgress);
      onUploaded(doc);
    } catch (err) {
      setError(err.message);
    } finally {
      setProgress(null);
    }
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function handleChoose(event) {
    const file = event.target.files[0];
    event.target.value = ""; // lets the user pick the same file again
    if (file) handleFile(file);
  }

  const uploading = progress !== null;

  return (
    <div>
      <div
        className={`dropzone ${dragging ? "dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <p><strong>Drag &amp; drop your file here</strong></p>
        <p className="hint">or click to browse · PDF or DOCX · max {MAX_MB} MB</p>
        <button
          type="button"
          className="btn"
          disabled={uploading}
          onClick={() => inputRef.current.click()}
        >
          Choose File
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          onChange={handleChoose}
          hidden
        />
        {uploading && (
          <div>
            <div className="progress"><div style={{ width: `${progress}%` }} /></div>
            <p className="hint">Uploading… {progress}%</p>
          </div>
        )}
      </div>
      {error && <p className="error" role="alert">{error}</p>}
    </div>
  );
}