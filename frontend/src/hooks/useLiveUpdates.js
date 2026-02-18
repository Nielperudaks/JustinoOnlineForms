import { useEffect, useRef } from "react"

export function useLiveUpdates({ onEvent, enabled = true }) {
  const socketRef = useRef(null)

  useEffect(() => {
    if (!enabled) return

    const ws = new WebSocket("ws://api.justinocorp.com/wss")
    socketRef.current = ws

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        onEvent?.(message)
      } catch {}
    }

    ws.onerror = () => {}
    ws.onclose = () => {}

    return () => {
      ws.close()
    }
  }, [enabled, onEvent])
}
