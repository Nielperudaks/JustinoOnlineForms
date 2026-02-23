import { useEffect, useRef } from "react"

export function useLiveUpdates({ onEvent, enabled = true }) {
  const socketRef = useRef(null)
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  useEffect(() => {
    if (!enabled) return

    const baseUrl = process.env.REACT_APP_BACKEND_URL || ""
    const wsUrl = baseUrl.startsWith("https")
      ? `wss://${baseUrl.replace("https://", "")}/ws`
      : baseUrl.startsWith("http")
        ? `ws://${baseUrl.replace("http://", "")}/ws`
        : `ws://${window.location.hostname}:8000/ws`

    const ws = new WebSocket(wsUrl)
    socketRef.current = ws

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        onEventRef.current?.(message)
      } catch {}
    }

    ws.onerror = () => {}
    ws.onclose = () => {}

    return () => {
      ws.close()
    }
  }, [enabled])
}
