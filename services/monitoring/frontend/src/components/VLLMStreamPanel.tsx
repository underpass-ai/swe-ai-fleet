import React, { useEffect, useState, useRef } from 'react';

interface VLLMStream {
  agent_id: string;
  stream_info: {
    task_description: string;
    role: string;
    status: string;
    model: string;
  };
  start_time: number;
  total_tokens: number;
  last_activity: number;
  is_complete: boolean;
}

interface VLLMStreamEvent {
  type: 'vllm_stream_start' | 'vllm_token' | 'vllm_stream_complete' | 'vllm_stream_active';
  agent_id: string;
  token?: string;
  position?: number;
  is_complete?: boolean;
  total_tokens?: number;
  stream_info?: any;
  timestamp: number;
}

export const VLLMStreamPanel: React.FC = () => {
  const [streams, setStreams] = useState<Map<string, VLLMStream>>(new Map());
  const [streamTexts, setStreamTexts] = useState<Map<string, string>>(new Map());
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const textAreaRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  useEffect(() => {
    const connectWebSocket = () => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/vllm-stream`;
        
        wsRef.current = new WebSocket(wsUrl);
        
        wsRef.current.onopen = () => {
          console.log('✅ vLLM Streaming WebSocket connected');
          setIsConnected(true);
          setError(null);
        };
        
        wsRef.current.onmessage = (event) => {
          try {
            const data: VLLMStreamEvent = JSON.parse(event.data);
            handleStreamEvent(data);
          } catch (err) {
            console.error('Failed to parse vLLM stream event:', err);
          }
        };
        
        wsRef.current.onclose = () => {
          console.log('❌ vLLM Streaming WebSocket disconnected');
          setIsConnected(false);
          // Reconnect after 3 seconds
          setTimeout(connectWebSocket, 3000);
        };
        
        wsRef.current.onerror = (error) => {
          console.error('vLLM Streaming WebSocket error:', error);
          setError('Connection error');
        };
        
      } catch (err) {
        console.error('Failed to connect to vLLM streaming:', err);
        setError('Failed to connect');
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleStreamEvent = (event: VLLMStreamEvent) => {
    const { type, agent_id, token, stream_info, total_tokens } = event;

    switch (type) {
      case 'vllm_stream_start':
      case 'vllm_stream_active':
        if (stream_info) {
          setStreams(prev => {
            const newStreams = new Map(prev);
            newStreams.set(agent_id, {
              agent_id,
              stream_info,
              start_time: Date.now(),
              total_tokens: 0,
              last_activity: Date.now(),
              is_complete: false
            });
            return newStreams;
          });
          setStreamTexts(prev => {
            const newTexts = new Map(prev);
            newTexts.set(agent_id, '');
            return newTexts;
          });
        }
        break;

      case 'vllm_token':
        if (token) {
          setStreamTexts(prev => {
            const newTexts = new Map(prev);
            const currentText = newTexts.get(agent_id) || '';
            newTexts.set(agent_id, currentText + token);
            return newTexts;
          });
          
          // Auto-scroll to bottom
          setTimeout(() => {
            const textArea = textAreaRefs.current.get(agent_id);
            if (textArea) {
              textArea.scrollTop = textArea.scrollHeight;
            }
          }, 10);
        }
        break;

      case 'vllm_stream_complete':
        setStreams(prev => {
          const newStreams = new Map(prev);
          const stream = newStreams.get(agent_id);
          if (stream) {
            newStreams.set(agent_id, {
              ...stream,
              is_complete: true,
              total_tokens: total_tokens || stream.total_tokens,
              last_activity: Date.now()
            });
          }
          return newStreams;
        });
        
        // Remove completed streams after 30 seconds
        setTimeout(() => {
          setStreams(prev => {
            const newStreams = new Map(prev);
            newStreams.delete(agent_id);
            return newStreams;
          });
          setStreamTexts(prev => {
            const newTexts = new Map(prev);
            newTexts.delete(agent_id);
            return newTexts;
          });
        }, 30000);
        break;
    }
  };

  // Remove test controls - only show real data

  const formatDuration = (startTime: number): string => {
    const duration = Math.floor((Date.now() - startTime) / 1000);
    const minutes = Math.floor(duration / 60);
    const seconds = duration % 60;
    return `${minutes}m ${seconds}s`;
  };

  const getRoleEmoji = (role: string): string => {
    const roleEmojis: Record<string, string> = {
      'DEV': '🧑‍💻',
      'QA': '🧪',
      'ARCHITECT': '🏗️',
      'DEVOPS': '⚙️',
      'DATA': '📊'
    };
    return roleEmojis[role] || '🤖';
  };

  const getRoleColor = (role: string): string => {
    const roleColors: Record<string, string> = {
      'DEV': 'bg-blue-500/20 text-blue-400',
      'QA': 'bg-green-500/20 text-green-400',
      'ARCHITECT': 'bg-purple-500/20 text-purple-400',
      'DEVOPS': 'bg-orange-500/20 text-orange-400',
      'DATA': 'bg-cyan-500/20 text-cyan-400'
    };
    return roleColors[role] || 'bg-gray-500/20 text-gray-400';
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6 shadow-lg space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-700 pb-4">
        <h2 className="text-2xl font-bold text-white flex items-center space-x-2">
          <span>🤖</span>
          <span>vLLM Live Streaming</span>
        </h2>
        <div className="flex items-center space-x-4">
          <div className={`px-3 py-1 rounded-full text-sm font-semibold ${
            isConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
          }`}>
            {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
          </div>
          <div className="text-sm text-gray-400">
            {streams.size} active stream{streams.size !== 1 ? 's' : ''}
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 text-red-400 text-sm">
          ❌ {error}
        </div>
      )}

      {/* Real-time Status */}
      <div className="bg-gray-700/50 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-white mb-3">Live vLLM Streaming</h3>
        <div className="text-sm text-gray-400">
          <p>📡 Connected to real vLLM agents via Ray cluster</p>
          <p>🔄 Streams update automatically when agents start deliberating</p>
          <p>⚡ Text appears character by character as agents think and respond</p>
        </div>
      </div>

      {/* Active Streams */}
      {streams.size === 0 ? (
        <div className="bg-gray-700/50 rounded-lg p-8 text-center text-gray-400">
          <span className="text-4xl mb-4 block">💤</span>
          <p>No active vLLM streams</p>
          <p className="text-sm mt-2">Streams will appear automatically when agents start deliberating</p>
          <p className="text-xs mt-1 text-gray-500">Trigger a deliberation via the Orchestrator to see live streaming</p>
        </div>
      ) : (
        <div className="space-y-4">
          {Array.from(streams.values()).map((stream) => {
            const streamText = streamTexts.get(stream.agent_id) || '';
            const isComplete = stream.is_complete;
            
            return (
              <div key={stream.agent_id} className="bg-gray-700/50 rounded-lg p-4">
                {/* Stream Header */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <span className="text-2xl">{getRoleEmoji(stream.stream_info.role)}</span>
                    <div>
                      <div className="font-semibold text-white">{stream.agent_id}</div>
                      <div className={`inline-block px-2 py-1 rounded text-xs font-semibold ${getRoleColor(stream.stream_info.role)}`}>
                        {stream.stream_info.role}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3 text-sm text-gray-400">
                    <div className={`px-2 py-1 rounded ${
                      isComplete ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
                    }`}>
                      {isComplete ? '✅ Complete' : '⏳ Streaming'}
                    </div>
                    <div>⏱️ {formatDuration(stream.start_time)}</div>
                    <div>📝 {streamText.length} chars</div>
                  </div>
                </div>

                {/* Task Description */}
                <div className="mb-3 p-3 bg-gray-800/50 rounded text-sm">
                  <div className="text-gray-400 mb-1">Task:</div>
                  <div className="text-white">{stream.stream_info.task_description}</div>
                </div>

                {/* Streaming Text */}
                <div 
                  ref={(el) => {
                    if (el) textAreaRefs.current.set(stream.agent_id, el);
                  }}
                  className="bg-black/50 rounded-lg p-4 font-mono text-sm text-green-400 max-h-64 overflow-y-auto whitespace-pre-wrap"
                  style={{ minHeight: '100px' }}
                >
                  {streamText}
                  {!isComplete && (
                    <span className="animate-pulse">▊</span>
                  )}
                </div>

                {/* Stream Stats */}
                <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
                  <div>Model: {stream.stream_info.model}</div>
                  <div>Last activity: {new Date(stream.last_activity).toLocaleTimeString()}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
