import { useWebSocket } from './hooks/useWebSocket';
import { SystemOverview } from './components/SystemOverview';
import { EventStream } from './components/EventStream';
import { CouncilsPanel } from './components/CouncilsPanel';
import { Neo4jPanel } from './components/Neo4jPanel';
import { ValKeyPanel } from './components/ValKeyPanel';
import { RayPanel } from './components/RayPanel';
import { VLLMStreamPanel } from './components/VLLMStreamPanel';
import { AdminPanel } from './components/AdminPanel';
import { AlertCircle } from 'lucide-react';

function App() {
  const { events, isConnected, error } = useWebSocket('/ws');

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-[1920px] mx-auto space-y-6">
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

        {/* Admin Control Panel - Full Width */}
        <div className="w-full">
          <AdminPanel />
        </div>

        {/* Ray Execution Panel - Full Width */}
        <div className="w-full">
          <RayPanel />
        </div>

        {/* vLLM Live Streaming Panel - Full Width */}
        <div className="w-full">
          <VLLMStreamPanel />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-3 gap-6" style={{ height: 'calc(100vh - 700px)' }}>
          {/* Left Column - Councils */}
          <div className="col-span-1">
            <CouncilsPanel />
          </div>
          
          {/* Center Column - Event Stream */}
          <div className="col-span-1">
            <EventStream events={events} />
          </div>
          
          {/* Right Column - Data Stores */}
          <div className="col-span-1 space-y-6">
            <div className="h-1/2">
              <Neo4jPanel />
            </div>
            <div className="h-1/2">
              <ValKeyPanel />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;

