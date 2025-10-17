import { useMemo } from 'react';
import type { Event } from '../types';
import { Activity, Database, Cpu, Box } from 'lucide-react';

interface EventStreamProps {
  events: Event[];
}

const getEventIcon = (source: string) => {
  switch (source) {
    case 'NATS':
      return <Activity className="w-4 h-4" />;
    case 'Neo4j':
      return <Database className="w-4 h-4" />;
    case 'Ray':
      return <Cpu className="w-4 h-4" />;
    default:
      return <Box className="w-4 h-4" />;
  }
};

const getEventColor = (subject: string) => {
  if (subject.includes('planning')) return 'text-blue-400';
  if (subject.includes('orchestration')) return 'text-green-400';
  if (subject.includes('context')) return 'text-purple-400';
  if (subject.includes('agent')) return 'text-yellow-400';
  return 'text-gray-400';
};

const formatTimestamp = (timestamp: string) => {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  } catch {
    return timestamp;
  }
};

export const EventStream = ({ events }: EventStreamProps) => {
  const sortedEvents = useMemo(() => {
    return [...events].sort((a, b) => 
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }, [events]);

  return (
    <div className="bg-panel rounded-lg p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-text flex items-center gap-2">
          <Activity className="w-5 h-5" />
          Event Stream
        </h2>
        <span className="text-sm text-muted">
          {events.length} events
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 font-mono text-sm">
        {sortedEvents.length === 0 ? (
          <div className="text-center text-muted py-8">
            <Activity className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>Waiting for events...</p>
            <p className="text-xs mt-1">Events will appear here in real-time</p>
          </div>
        ) : (
          sortedEvents.map((event, index) => (
            <div
              key={`${event.timestamp}-${index}`}
              className="bg-background border border-border rounded p-3 hover:border-blue-500/50 transition-colors event-enter"
            >
              <div className="flex items-start gap-3">
                <div className="mt-1 text-muted">
                  {getEventIcon(event.source)}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-muted">
                      {formatTimestamp(event.timestamp)}
                    </span>
                    <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded">
                      {event.source}
                    </span>
                  </div>
                  
                  <div className={`font-bold mb-1 ${getEventColor(event.subject || event.type)}`}>
                    {event.subject || event.type}
                  </div>
                  
                  {event.data && (
                    <div className="text-xs text-muted space-y-1">
                      {event.data.story_id && (
                        <div>Story: <span className="text-text">{event.data.story_id}</span></div>
                      )}
                      {event.data.task_id && (
                        <div>Task: <span className="text-text">{event.data.task_id}</span></div>
                      )}
                      {event.data.role && (
                        <div>Role: <span className="text-text">{event.data.role}</span></div>
                      )}
                      {event.data.event_type && (
                        <div>Type: <span className="text-text">{event.data.event_type}</span></div>
                      )}
                    </div>
                  )}
                  
                  {event.metadata && (
                    <div className="text-xs text-muted mt-2 flex gap-3">
                      {event.metadata.stream && (
                        <span>Stream: {event.metadata.stream}</span>
                      )}
                      {event.metadata.sequence && (
                        <span>Seq: {event.metadata.sequence}</span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

