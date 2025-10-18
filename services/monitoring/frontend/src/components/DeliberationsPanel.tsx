import { useEffect, useState } from 'react';

interface Deliberation {
  task_id: string;
  agent_id: string;
  role: string;
  status: string;
  duration_ms: number;
  timestamp: string;
  has_proposal: boolean;
  num_operations: number;
  model: string;
}

export function DeliberationsPanel() {
  const [deliberations, setDeliberations] = useState<Deliberation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchDeliberations = async () => {
    try {
      const response = await fetch('/api/deliberations/recent?limit=20');
      const data = await response.json() as {
        deliberations?: Deliberation[];
        error?: string;
      };
      
      if (data.error) {
        setError(data.error);
      } else {
        setDeliberations(data.deliberations || []);
        setError(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch deliberations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchDeliberations();
    
    if (autoRefresh) {
      const interval = setInterval(() => {
        void fetchDeliberations();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-400';
      case 'failed': return 'text-red-400';
      default: return 'text-yellow-400';
    }
  };

  const getRoleColor = (role: string) => {
    const colors: Record<string, string> = {
      'DEV': 'bg-blue-500/20 text-blue-300',
      'QA': 'bg-green-500/20 text-green-300',
      'ARCHITECT': 'bg-purple-500/20 text-purple-300',
      'DEVOPS': 'bg-orange-500/20 text-orange-300',
      'DATA': 'bg-pink-500/20 text-pink-300',
    };
    return colors[role] || 'bg-gray-500/20 text-gray-300';
  };

  return (
    <div className="bg-slate-800 rounded-lg p-6 shadow-lg">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold text-blue-400">
          🎯 Recent Deliberations
        </h2>
        <div className="flex gap-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`px-3 py-1 rounded text-sm ${
              autoRefresh
                ? 'bg-green-500 text-white'
                : 'bg-gray-600 text-gray-300'
            }`}
          >
            {autoRefresh ? '🔄 Auto' : '⏸️ Paused'}
          </button>
          <button
            onClick={() => void fetchDeliberations()}
            className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
          >
            🔃 Refresh
          </button>
        </div>
      </div>

      {loading && (
        <div className="text-center text-gray-400 py-8">
          Loading deliberations...
        </div>
      )}

      {error && (
        <div className="bg-red-500/20 border border-red-500 text-red-300 p-4 rounded mb-4">
          ❌ Error: {error}
        </div>
      )}

      {!loading && !error && deliberations.length === 0 && (
        <div className="text-center text-gray-400 py-8">
          No deliberations found. Execute a test case to see results here.
        </div>
      )}

      {!loading && deliberations.length > 0 && (
        <div className="space-y-3">
          {deliberations.map((delib, idx) => (
            <div
              key={`${delib.task_id}-${delib.agent_id}-${idx}`}
              className="bg-slate-700/50 rounded p-4 border border-slate-600"
            >
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded text-xs font-mono ${getRoleColor(delib.role)}`}>
                    {delib.role}
                  </span>
                  <span className="text-gray-400 text-sm font-mono">
                    {delib.agent_id}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-semibold ${getStatusColor(delib.status)}`}>
                    {delib.status === 'completed' ? '✅' : '❌'} {delib.status}
                  </span>
                  <span className="text-gray-500 text-xs">
                    {delib.duration_ms}ms
                  </span>
                </div>
              </div>

              <div className="text-gray-300 text-sm mb-2">
                📝 Task: <span className="font-mono text-blue-300">{delib.task_id}</span>
              </div>

              <div className="flex gap-4 text-xs text-gray-400">
                <span>🤖 {delib.model}</span>
                {delib.has_proposal && <span>💡 Has Proposal</span>}
                {delib.num_operations > 0 && (
                  <span>⚙️ {delib.num_operations} operations</span>
                )}
                <span className="ml-auto">
                  🕒 {new Date(delib.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-4 pt-4 border-t border-slate-700 text-sm text-gray-400">
        📊 Total: {deliberations.length} deliberations
        {autoRefresh && <span className="ml-4">🔄 Auto-refresh: 5s</span>}
      </div>
    </div>
  );
}

