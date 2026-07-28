'use client';

import { useEffect, useCallback, useRef, useState } from 'react';
import { wsClient, WebSocketEventHandler } from './websocket';

export interface UseWebSocketOptions {
  onConnect?: () => void;
  onDisconnect?: () => void;
  shouldConnect?: boolean;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { onConnect, onDisconnect, shouldConnect = true } = options;
  const [isConnected, setIsConnected] = useState(false);
  const handlersRef = useRef<Map<string, Set<WebSocketEventHandler>>>(new Map());

  useEffect(() => {
    if (!shouldConnect) return;

    const apiKey = typeof window !== 'undefined' ? localStorage.getItem('apiKey') : null;
    if (!apiKey) return;

    wsClient
      .connect(apiKey)
      .then(() => {
        setIsConnected(true);
        onConnect?.();
      })
      .catch((error) => {
        console.error('WebSocket connection failed:', error);
      });

    return () => {
      wsClient.disconnect();
      setIsConnected(false);
      onDisconnect?.();
    };
  }, [shouldConnect, onConnect, onDisconnect]);

  const on = useCallback((type: string, handler: WebSocketEventHandler) => {
    wsClient.on(type, handler);

    if (!handlersRef.current.has(type)) {
      handlersRef.current.set(type, new Set());
    }
    handlersRef.current.get(type)!.add(handler);

    return () => {
      wsClient.off(type, handler);
      handlersRef.current.get(type)?.delete(handler);
    };
  }, []);

  const send = useCallback((type: string, data: unknown) => {
    wsClient.send({ type, data });
  }, []);

  return {
    isConnected,
    on,
    send,
  };
}
