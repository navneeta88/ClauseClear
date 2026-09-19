// All communication with the Flask backend goes through this file.
const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:5000";

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) {
    throw new Error(`Server responded with status ${res.status}`);
  }
  return res.json();
}

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