import { useEffect, useState } from 'react';
import { Database, Circle } from 'lucide-react';

interface Neo4jStats {
  connected: boolean;
  total_nodes?: number;
  total_relationships?: number;
  nodes_by_label?: Array<{ labels: string[]; count: number }>;
  relationships_by_type?: Array<{ type: string; count: number }>;
  error?: string;
}

export const Neo4jPanel = () => {
  const [stats, setStats] = useState<Neo4jStats | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('/api/neo4j/stats');
        const data = await response.json();
        setStats(data);
      } catch (error) {
        console.error('Failed to fetch Neo4j stats:', error);
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

  return (
    <div className="bg-panel rounded-lg p-4 h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-text flex items-center gap-2">
          <Database className="w-5 h-5" />
          Neo4j Graph
        </h2>
        <div className="flex items-center gap-2">
          <Circle className={`w-2 h-2 ${stats.connected ? 'fill-green-500 text-green-500' : 'fill-red-500 text-red-500'}`} />
          <span className="text-xs text-muted">
            {stats.connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {!stats.connected ? (
        <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 text-center">
          <div className="text-red-400 text-sm">
            ❌ Neo4j not connected
          </div>
          {stats.error && (
            <div className="text-xs text-red-300 mt-2">
              {stats.error}
            </div>
          )}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="bg-background border border-border rounded-lg p-3">
              <div className="text-2xl font-bold text-blue-400">{stats.total_nodes || 0}</div>
              <div className="text-xs text-muted">Total Nodes</div>
            </div>
            <div className="bg-background border border-border rounded-lg p-3">
              <div className="text-2xl font-bold text-green-400">{stats.total_relationships || 0}</div>
              <div className="text-xs text-muted">Relationships</div>
            </div>
          </div>

          <div className="space-y-3">
            <div>
              <div className="text-sm font-medium text-text mb-2">Nodes by Label</div>
              <div className="space-y-1">
                {(stats.nodes_by_label || []).length > 0 ? (
                  stats.nodes_by_label?.map((node, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between text-xs font-mono"
                    >
                      <span className="text-muted">{node.labels.join(', ')}</span>
                      <span className="text-text font-bold">{node.count}</span>
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-muted text-center py-2">No nodes yet</div>
                )}
              </div>
            </div>

            <div>
              <div className="text-sm font-medium text-text mb-2">Relationships</div>
              <div className="space-y-1">
                {(stats.relationships_by_type || []).length > 0 ? (
                  stats.relationships_by_type?.map((rel, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between text-xs font-mono"
                    >
                      <span className="text-muted">{rel.type}</span>
                      <span className="text-text font-bold">{rel.count}</span>
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-muted text-center py-2">No relationships yet</div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

