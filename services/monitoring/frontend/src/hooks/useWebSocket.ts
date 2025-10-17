import { useEffect, useState, useCallback, useRef } from 'react';
import type { Event } from '../types';

interface UseWebSocketReturn {
  events: Event[];
  isConnected: boolean;
  error: string | null;
  sendMessage: (message: string) => void;
}

export const useWebSocket = (url: string): UseWebSocketReturn => {
  const [events, setEvents] = useState<Event[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout>();
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 10;

  const connect = useCallback(() => {
    try {
      console.log('🔌 Connecting to WebSocket:', url);
      
      // Build WebSocket URL
      const wsUrl = url.startsWith('ws') 
        ? url 
        : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;
      
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('✅ WebSocket connected');
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Ignore pong messages
          if (data === 'pong') return;
          
          console.log('📨 Received event:', data.type || data.subject);
          
          setEvents((prev) => {
            const newEvents = [data, ...prev];
            // Keep only last 100 events
            return newEvents.slice(0, 100);
          });
        } catch (err) {
          console.error('❌ Failed to parse message:', err);
        }
      };

      ws.current.onerror = (event) => {
        console.error('❌ WebSocket error:', event);
        setError('WebSocket connection error');
      };

      ws.current.onclose = () => {
        console.log('🔌 WebSocket disconnected');
        setIsConnected(false);
        
        // Attempt to reconnect
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const timeout = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          console.log(`🔄 Reconnecting in ${timeout/1000}s (attempt ${reconnectAttempts.current + 1}/${maxReconnectAttempts})`);
          
          reconnectTimeout.current = setTimeout(() => {
            reconnectAttempts.current += 1;
            connect();
          }, timeout);
        } else {
          setError('Failed to connect after multiple attempts');
        }
      };
    } catch (err) {
      console.error('❌ Failed to create WebSocket:', err);
      setError('Failed to create WebSocket connection');
    }
  }, [url]);

  const sendMessage = useCallback((message: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(message);
    } else {
      console.warn('⚠️  WebSocket is not connected');
    }
  }, []);

  useEffect(() => {
    connect();

    // Heartbeat to keep connection alive
    const heartbeat = setInterval(() => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.send('ping');
      }
    }, 30000);

    return () => {
      clearInterval(heartbeat);
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [connect]);

  return {
    events,
    isConnected,
    error,
    sendMessage,
  };
};

