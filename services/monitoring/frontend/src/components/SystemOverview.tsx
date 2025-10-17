import { Server, Database, Activity, Cpu } from 'lucide-react';

interface SystemOverviewProps {
  isConnected: boolean;
  eventCount: number;
}

export const SystemOverview = ({ isConnected, eventCount }: SystemOverviewProps) => {
  const services = [
    { name: 'Monitoring Dashboard', status: isConnected ? 'running' : 'disconnected', icon: Activity },
    { name: 'NATS JetStream', status: 'running', icon: Server },
    { name: 'Orchestrator', status: 'running', icon: Cpu },
    { name: 'Context Service', status: 'running', icon: Database },
  ];

  return (
    <div className="bg-panel rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-text">
          🎯 SWE AI Fleet - Monitoring Dashboard
        </h1>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'} animate-pulse`} />
            <span className="text-sm text-muted">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <div className="text-sm text-muted">
            Events: <span className="text-text font-bold">{eventCount}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {services.map((service) => {
          const Icon = service.icon;
          const isRunning = service.status === 'running';
          
          return (
            <div
              key={service.name}
              className="bg-background border border-border rounded-lg p-4 hover:border-blue-500/50 transition-colors"
            >
              <div className="flex items-center gap-3 mb-2">
                <Icon className={`w-5 h-5 ${isRunning ? 'text-green-400' : 'text-red-400'}`} />
                <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-green-500' : 'bg-red-500'}`} />
              </div>
              <div className="text-sm font-medium text-text">{service.name}</div>
              <div className="text-xs text-muted mt-1">{service.status}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

