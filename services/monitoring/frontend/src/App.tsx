import { useWebSocket } from './hooks/useWebSocket';
import { SystemOverview } from './components/SystemOverview';
import { EventStream } from './components/EventStream';
import { AlertCircle } from 'lucide-react';

function App() {
  const { events, isConnected, error } = useWebSocket('/ws');

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* System Overview */}
        <SystemOverview isConnected={isConnected} eventCount={events.length} />

        {/* Error Alert */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <div>
              <div className="font-bold text-red-500">Connection Error</div>
              <div className="text-sm text-red-400">{error}</div>
            </div>
          </div>
        )}

        {/* Main Content */}
        <div className="grid grid-cols-1 gap-6" style={{ height: 'calc(100vh - 250px)' }}>
          {/* Event Stream */}
          <EventStream events={events} />
        </div>
      </div>
    </div>
  );
}

export default App;

