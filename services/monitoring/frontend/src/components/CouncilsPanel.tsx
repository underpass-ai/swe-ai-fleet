import { useEffect, useState } from 'react';
import { Users, Circle } from 'lucide-react';

interface Council {
  role: string;
  emoji: string;
  agents: Array<{ id: string; status: string }>;
  status: string;
  model: string;
  total_agents: number;
}

interface CouncilsData {
  connected: boolean;
  councils?: Council[];
  total_agents?: number;
  total_councils?: number;
  error?: string;
}

export const CouncilsPanel = () => {
  const [data, setData] = useState<CouncilsData | null>(null);

  useEffect(() => {
    const fetchCouncils = async () => {
      try {
        const response = await fetch('/api/councils');
        const result = await response.json();
        setData(result);
      } catch (error) {
        console.error('Failed to fetch councils:', error);
        setData({ connected: false, error: 'Failed to fetch councils' });
      }
    };

    fetchCouncils();
    const interval = setInterval(fetchCouncils, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!data) {
    return (
      <div className="bg-panel rounded-lg p-4 h-full">
        <div className="text-center text-muted">Loading...</div>
      </div>
    );
  }

  return (
    <div className="bg-panel rounded-lg p-4 h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-text flex items-center gap-2">
          <Users className="w-5 h-5" />
          Councils & Agents
        </h2>
        <div className="flex items-center gap-2">
          <Circle className={`w-2 h-2 ${data.connected ? 'fill-green-500 text-green-500' : 'fill-red-500 text-red-500'}`} />
          <span className="text-xs text-muted">
            {data.connected ? `${data.total_agents || 0} agents` : 'Disconnected'}
          </span>
        </div>
      </div>

      {!data.connected ? (
        <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 text-center">
          <div className="text-red-400 text-sm">
            ❌ Orchestrator not connected
          </div>
          {data.error && (
            <div className="text-xs text-red-300 mt-2">
              {data.error}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {(data.councils || []).map((council) => (
            <div
              key={council.role}
              className="bg-background border border-border rounded-lg p-3"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xl">{council.emoji}</span>
                  <span className="font-bold text-text">{council.role}</span>
                  <Circle className="w-2 h-2 fill-green-500 text-green-500" />
                </div>
                <span className="text-xs text-muted">{council.total_agents} agents</span>
              </div>
              
              <div className="text-xs text-muted mb-2">
                Model: {council.model}
              </div>
              
              <div className="space-y-1">
                {council.agents.map((agent) => (
                  <div
                    key={agent.id}
                    className="flex items-center gap-2 text-xs font-mono text-muted"
                  >
                    <Circle className="w-1.5 h-1.5 fill-blue-400 text-blue-400" />
                    {agent.id}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

