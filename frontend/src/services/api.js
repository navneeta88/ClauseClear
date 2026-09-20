// All communication with the Flask backend goes through this file.
const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:5000";

async function request(path, options) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, options);
  } catch {
    throw new Error("Could not reach the server. Is Flask running?");
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    // response was not JSON
  }
  if (!res.ok) {
    throw new Error((data && data.error) || `Request failed (status ${res.status}).`);
  }
  return data;
}

const postJson = (path, body) =>
  request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const checkHealth = () => request("/api/health");
export const simplifyDocument = (documentId) =>
  postJson("/api/simplify", { document_id: documentId });
export const analyzeRisks = (documentId) =>
  postJson("/api/analyze-risks", { document_id: documentId });
export const getChecklist = (documentId) =>
  postJson("/api/checklist", { document_id: documentId });
export const askQuestion = (documentId, question, history) =>
  postJson("/api/chat", { document_id: documentId, question, history });

// Uses XMLHttpRequest instead of fetch because fetch can't report upload progress.
export function uploadDocument(file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/upload`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      let data = {};
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        // response was not JSON; fall through to the generic error
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data);
      } else {
        reject(new Error(data.error || `Upload failed (status ${xhr.status}).`));
      }
    };

    xhr.onerror = () =>
      reject(new Error("Could not reach the server. Is Flask running?"));

    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}