import { useEffect, useState } from 'react';
import { Database, Circle } from 'lucide-react';

interface ValKeyStats {
  total_keys: number;
  memory_used_mb: number;
  hits: number;
  misses: number;
  recent_keys: Array<{ key: string; type: string; ttl: number }>;
  connected: boolean;
  error?: string;
}

export const ValKeyPanel = () => {
  const [stats, setStats] = useState<ValKeyStats | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('/api/valkey/stats');
        const data = await response.json();
        setStats(data);
      } catch (error) {
        console.error('Failed to fetch ValKey stats:', error);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!stats) {
    return (
      <div className="bg-panel rounded-lg p-4 h-full">
        <div className="text-center text-muted">Loading...</div>
      </div>
    );
  }

  const hitRate = stats.hits + stats.misses > 0
    ? ((stats.hits / (stats.hits + stats.misses)) * 100).toFixed(1)
    : '0';

  return (
    <div className="bg-panel rounded-lg p-4 h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-text flex items-center gap-2">
          <Database className="w-5 h-5" />
          ValKey Cache
        </h2>
        <div className="flex items-center gap-2">
          <Circle className={`w-2 h-2 ${stats.connected ? 'fill-green-500 text-green-500' : 'fill-red-500 text-red-500'}`} />
          <span className="text-xs text-muted">
            {stats.connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {!stats.connected && (
        <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 mb-4 text-center">
          <div className="text-red-400 text-sm">
            ❌ ValKey not connected
          </div>
          {stats.error && (
            <div className="text-xs text-red-300 mt-2">
              {stats.error}
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-4 gap-2 mb-4">
        <div className="bg-background border border-border rounded p-2">
          <div className="text-lg font-bold text-blue-400">{stats.total_keys}</div>
          <div className="text-xs text-muted">Keys</div>
        </div>
        <div className="bg-background border border-border rounded p-2">
          <div className="text-lg font-bold text-purple-400">{stats.memory_used_mb.toFixed(1)} MB</div>
          <div className="text-xs text-muted">Memory</div>
        </div>
        <div className="bg-background border border-border rounded p-2">
          <div className="text-lg font-bold text-green-400">{stats.hits}</div>
          <div className="text-xs text-muted">Hits</div>
        </div>
        <div className="bg-background border border-border rounded p-2">
          <div className="text-lg font-bold text-red-400">{stats.misses}</div>
          <div className="text-xs text-muted">Misses</div>
        </div>
      </div>

      <div className="mb-2">
        <div className="text-xs text-muted mb-1">Hit Rate: <span className="text-green-400 font-bold">{hitRate}%</span></div>
        <div className="bg-background h-2 rounded-full overflow-hidden">
          <div 
            className="bg-green-500 h-full transition-all duration-500"
            style={{ width: `${hitRate}%` }}
          />
        </div>
      </div>

      <div>
        <div className="text-sm font-medium text-text mb-2">Recent Keys</div>
        <div className="space-y-1 max-h-32 overflow-y-auto">
          {stats.recent_keys.map((key, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between text-xs font-mono bg-background border border-border rounded p-2"
            >
              <span className="text-muted truncate flex-1">{key.key}</span>
              <div className="flex items-center gap-2 ml-2">
                <span className="text-purple-400">{key.type}</span>
                {key.ttl > 0 && (
                  <span className="text-yellow-400">{key.ttl}s</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

