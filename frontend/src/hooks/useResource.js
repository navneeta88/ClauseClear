import { useCallback, useRef, useState } from "react";

// Loads data on demand, remembers the result, and supports retry.
// The inFlight guard stops React's dev-mode double effect from calling the AI twice.
export function useResource(loader) {
  const [state, setState] = useState({ status: "idle", data: null, error: "" });
  const inFlight = useRef(false);

  const load = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setState({ status: "loading", data: null, error: "" });
    try {
      const data = await loader();
      setState({ status: "done", data, error: "" });
    } catch (err) {
      setState({ status: "error", data: null, error: err.message });
    } finally {
      inFlight.current = false;
    }
  }, [loader]);

  return [state, load];
}