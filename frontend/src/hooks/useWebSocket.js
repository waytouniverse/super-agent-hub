import { useState, useCallback } from 'react';

export function useWebSocket() {
  const [ws, setWs] = useState(null);
  const [connecting, setConnecting] = useState(false);

  const connect = useCallback((engine) => {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${location.host}/ws/chat/${engine}`;
    const socket = new WebSocket(url);
    setConnecting(true);
    socket.onopen = () => setConnecting(false);
    socket.onerror = () => setConnecting(false);
    setWs(socket);
    return socket;
  }, []);

  const disconnect = useCallback(() => {
    if (ws) {
      ws.close();
      setWs(null);
    }
  }, [ws]);

  return { ws, connecting, connect, disconnect };
}
