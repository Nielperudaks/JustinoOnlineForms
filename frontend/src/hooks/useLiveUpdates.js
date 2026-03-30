import { useEffect, useRef } from "react";

const HEARTBEAT_INTERVAL_MS = 25000;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 10000;

export function useLiveUpdates({ onEvent, enabled = true }) {
  const socketRef = useRef(null);
  const onEventRef = useRef(onEvent);
  const reconnectTimeoutRef = useRef(null);
  const heartbeatIntervalRef = useRef(null);
  const reconnectAttemptRef = useRef(0);
  const shouldReconnectRef = useRef(enabled);

  onEventRef.current = onEvent;
  shouldReconnectRef.current = enabled;

  useEffect(() => {
    if (!enabled) {
      return undefined;
    }

    const baseUrl = process.env.REACT_APP_BACKEND_URL || "";
    const wsUrl = baseUrl.startsWith("https")
      ? `wss://${baseUrl.replace("https://", "")}/ws`
      : baseUrl.startsWith("http")
        ? `ws://${baseUrl.replace("http://", "")}/ws`
        : `ws://${window.location.hostname}:8000/ws`;

    const clearHeartbeat = () => {
      if (heartbeatIntervalRef.current) {
        window.clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = null;
      }
    };

    const clearReconnectTimeout = () => {
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };

    const scheduleReconnect = () => {
      if (!shouldReconnectRef.current) {
        return;
      }

      clearReconnectTimeout();
      const delay = Math.min(
        RECONNECT_BASE_MS * (2 ** reconnectAttemptRef.current),
        RECONNECT_MAX_MS
      );
      reconnectAttemptRef.current += 1;
      reconnectTimeoutRef.current = window.setTimeout(connect, delay);
    };

    const startHeartbeat = (ws) => {
      clearHeartbeat();
      heartbeatIntervalRef.current = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send("ping");
        }
      }, HEARTBEAT_INTERVAL_MS);
    };

    const connect = () => {
      clearReconnectTimeout();
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        reconnectAttemptRef.current = 0;
        startHeartbeat(ws);
      };

      ws.onmessage = (event) => {
        if (event.data === "pong") {
          return;
        }

        try {
          const message = JSON.parse(event.data);
          onEventRef.current?.(message);
        } catch {}
      };

      ws.onerror = () => {
        ws.close();
      };

      ws.onclose = () => {
        clearHeartbeat();
        if (socketRef.current === ws) {
          socketRef.current = null;
        }
        scheduleReconnect();
      };
    };

    connect();

    return () => {
      shouldReconnectRef.current = false;
      clearHeartbeat();
      clearReconnectTimeout();
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [enabled]);
}
