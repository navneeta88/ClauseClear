import { useEffect } from "react";

const FALLBACK_DISCLAIMER =
  "This explanation is for informational purposes only and is not a substitute for advice from a qualified lawyer.";

export function Loading({ text }) {
  return (
    <div className="status-box" role="status">
      <span className="spinner" aria-hidden="true" />
      <p>{text}</p>
    </div>
  );
}

export function ErrorBox({ message, onRetry }) {
  return (
    <div className="error-box" role="alert">
      <p><strong>Something went wrong</strong></p>
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="btn" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function Empty({ text }) {
  return <p className="empty">{text}</p>;
}

export function Disclaimer({ text }) {
  return <p className="disclaimer">ⓘ {text || FALLBACK_DISCLAIMER}</p>;
}

// Shows loading / error / result for a resource, and starts loading on first view.
export function ResourceView({ resource, load, loadingText, children }) {
  useEffect(() => {
    if (resource.status === "idle") load();
  }, [resource.status, load]);

  if (resource.status === "idle" || resource.status === "loading") {
    return <Loading text={loadingText} />;
  }
  if (resource.status === "error") {
    return <ErrorBox message={resource.error} onRetry={load} />;
  }
  return children(resource.data);
}