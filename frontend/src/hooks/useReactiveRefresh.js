import { useEffect, useRef } from "react";

/**
 * Keeps data reactive by refetching at an interval and when the user
 * returns to the tab. Use for requests, approvals, stats, notifications.
 *
 * @param {() => void | Promise<void>} refetch - Function to call to refresh data
 * @param {Object} options
 * @param {number} [options.intervalMs=60000] - Polling interval in ms (default 15s)
 * @param {boolean} [options.refetchOnFocus=true] - Refetch when window gains focus
 * @param {boolean} [options.enabled=true] - Whether polling/focus refetch is active
 */
export function useReactiveRefresh(refetch, options = {}) {
  const {
    intervalMs = 60000,
    refetchOnFocus = true,
    enabled = true,
  } = options;

  const refetchRef = useRef(refetch);
  refetchRef.current = refetch;

  useEffect(() => {
    if (!enabled || typeof refetchRef.current !== "function") return;

    const tick = () => {
      const fn = refetchRef.current;
      if (fn) Promise.resolve(fn()).catch(() => {});
    };

    const id = setInterval(tick, intervalMs);

    if (!refetchOnFocus) return () => clearInterval(id);

    const onFocus = () => {
      if (document.visibilityState === "visible") tick();
    };
    document.addEventListener("visibilitychange", onFocus);

    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onFocus);
    };
  }, [enabled, intervalMs, refetchOnFocus]);
}
