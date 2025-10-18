import { useEffect, useState } from 'react';
import { Server, Database, Activity, Cpu, Zap } from 'lucide-react';

interface Service {
  name: string;
  status: 'running' | 'disconnected' | 'error';
  icon: string;
}

interface SystemOverviewProps {
  isConnected: boolean;
  eventCount: number;
}

export const SystemOverview = ({ isConnected, eventCount }: SystemOverviewProps) => {
  const [services, setServices] = useState<Service[]>([]);

  useEffect(() => {
    const fetchSystemStatus = async () => {
      try {
        const response = await fetch('/api/system/status');
        const data = await response.json() as { services?: Service[] };
        setServices(data.services || []);
      } catch (error) {
        console.error('Failed to fetch system status:', error);
        // Fallback to basic status
        setServices([
          { name: 'Monitoring Dashboard', status: isConnected ? 'running' : 'disconnected', icon: 'Activity' },
          { name: 'NATS JetStream', status: 'error', icon: 'Server' },
          { name: 'Orchestrator', status: 'error', icon: 'Cpu' },
          { name: 'Context Service', status: 'error', icon: 'Database' },
          { name: 'Ray Executor', status: 'error', icon: 'Zap' },
        ]);
      }
    };

    void fetchSystemStatus();
    const interval = setInterval(() => {
      void fetchSystemStatus();
    }, 10000); // Check every 10 seconds
    return () => clearInterval(interval);
  }, [isConnected]);

  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'Server': return Server;
      case 'Database': return Database;
      case 'Activity': return Activity;
      case 'Cpu': return Cpu;
      case 'Zap': return Zap;
      default: return Activity;
    }
  };

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

      <div className="grid grid-cols-5 gap-4">
        {services.map((service) => {
          const Icon = getIcon(service.icon);
          const isRunning = service.status === 'running';
          const isError = service.status === 'error';
          
          return (
            <div
              key={service.name}
              className="bg-background border border-border rounded-lg p-4 hover:border-blue-500/50 transition-colors"
            >
              <div className="flex items-center gap-3 mb-2">
                <Icon className={`w-5 h-5 ${
                  isRunning ? 'text-green-400' : 
                  isError ? 'text-red-400' : 'text-yellow-400'
                }`} />
                <div className={`w-2 h-2 rounded-full ${
                  isRunning ? 'bg-green-500' : 
                  isError ? 'bg-red-500' : 'bg-yellow-500'
                }`} />
              </div>
              <div className="text-sm font-medium text-text">{service.name}</div>
              <div className={`text-xs mt-1 ${
                isRunning ? 'text-green-400' : 
                isError ? 'text-red-400' : 'text-yellow-400'
              }`}>
                {service.status}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

