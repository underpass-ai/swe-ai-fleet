import React, { useEffect, useState } from 'react';

interface RayExecutorStats {
  connected: boolean;
  status?: string;
  uptime?: string;
  total_deliberations?: number;
  active_deliberations?: number;
  completed_deliberations?: number;
  failed_deliberations?: number;
  average_execution_time_ms?: number;
  version?: string;
  python_version?: string;
  ray_version?: string;
  error?: string;
}

interface RayClusterStats {
  connected: boolean;
  status?: string;
  nodes?: {
    total: number;
    alive: number;
  };
  resources?: {
    cpus: {
      total: number;
      used: number;
      available: number;
    };
    gpus: {
      total: number;
      used: number;
      available: number;
    };
    memory_gb: {
      total: number;
      used: number;
      available: number;
    };
  };
  jobs?: {
    active: number;
    completed: number;
    failed: number;
  };
  python_version?: string;
  ray_version?: string;
  error?: string;
}

interface RayJob {
  job_id: string;
  name: string;
  status: string;
  submission_id: string;
  role: string;
  task_id: string;
  start_time: string;
  end_time?: string;
  runtime: string;
}

export const RayPanel: React.FC = () => {
  const [executorStats, setExecutorStats] = useState<RayExecutorStats | null>(null);
  const [clusterStats, setClusterStats] = useState<RayClusterStats | null>(null);
  const [activeJobs, setActiveJobs] = useState<RayJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Fetch all Ray data in parallel
        const [executorRes, clusterRes, jobsRes] = await Promise.all([
          fetch('/api/ray/executor'),
          fetch('/api/ray/cluster'),
          fetch('/api/ray/jobs')
        ]);

        if (!executorRes.ok || !clusterRes.ok || !jobsRes.ok) {
          throw new Error('Failed to fetch Ray data');
        }

        const executorData = await executorRes.json() as RayExecutorStats;
        const clusterData = await clusterRes.json() as RayClusterStats;
        const jobsData = await jobsRes.json() as { active_jobs?: RayJob[] };

        setExecutorStats(executorData);
        setClusterStats(clusterData);
        setActiveJobs(jobsData.active_jobs || []);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    void fetchData();
    const interval = setInterval(() => {
      void fetchData();
    }, 5000); // Refresh every 5 seconds

    return () => clearInterval(interval);
  }, []);

  const getResourcePercentage = (used: number, total: number): number => {
    return (used / total) * 100;
  };

  const getResourceColor = (percentage: number): string => {
    if (percentage > 90) return 'bg-red-500';
    if (percentage > 70) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  if (loading && !executorStats) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
        <div className="flex items-center space-x-2">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500" />
          <span className="text-gray-300">Loading Ray stats...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 shadow-lg">
        <div className="text-red-400">❌ Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6 shadow-lg space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-700 pb-4">
        <h2 className="text-2xl font-bold text-white flex items-center space-x-2">
          <span>⚡</span>
          <span>Ray Distributed Execution</span>
        </h2>
        <div className={`px-3 py-1 rounded-full text-sm font-semibold ${
          executorStats?.status === 'healthy' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
        }`}>
          {executorStats?.status === 'healthy' ? '✅ Healthy' : '❌ Unhealthy'}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Ray Executor Service */}
        <div className="bg-gray-700/50 rounded-lg p-4 space-y-3">
          <h3 className="text-lg font-semibold text-blue-400 flex items-center space-x-2">
            <span>🔧</span>
            <span>Ray Executor Service</span>
          </h3>
          
          {executorStats ? (
            executorStats.connected ? (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Status:</span>
                  <span className="text-green-400 font-semibold">{executorStats.status || 'healthy'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Uptime:</span>
                  <span className="text-white">{executorStats.uptime || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Python:</span>
                  <span className="text-white font-mono">{executorStats.python_version || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Ray:</span>
                  <span className="text-white font-mono">{executorStats.ray_version || 'N/A'}</span>
                </div>
                
                <div className="border-t border-gray-600 pt-3 mt-3 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Total Deliberations:</span>
                    <span className="text-blue-400 font-semibold">{executorStats.total_deliberations || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Active:</span>
                    <span className="text-yellow-400 font-semibold">{executorStats.active_deliberations || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Completed:</span>
                    <span className="text-green-400 font-semibold">{executorStats.completed_deliberations || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Failed:</span>
                    <span className="text-red-400 font-semibold">{executorStats.failed_deliberations || 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Avg Time:</span>
                    <span className="text-white font-semibold">{executorStats.average_execution_time_ms?.toFixed(1) || '0.0'} ms</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 text-center">
                <div className="text-red-400 text-sm">
                  ❌ Ray Executor not connected
                </div>
                {executorStats.error && (
                  <div className="text-xs text-red-300 mt-2">
                    {executorStats.error}
                  </div>
                )}
              </div>
            )
          ) : (
            <div className="text-center text-gray-400">Loading...</div>
          )}
        </div>

        {/* Ray Cluster */}
        <div className="bg-gray-700/50 rounded-lg p-4 space-y-3">
          <h3 className="text-lg font-semibold text-purple-400 flex items-center space-x-2">
            <span>🖥️</span>
            <span>Ray Cluster</span>
          </h3>
          
          {clusterStats ? (
            clusterStats.connected ? (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Python:</span>
                  <span className="text-white font-mono">{clusterStats.python_version || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Ray:</span>
                  <span className="text-white font-mono">{clusterStats.ray_version || 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Nodes:</span>
                  <span className="text-white">{clusterStats.nodes?.alive || 0} / {clusterStats.nodes?.total || 0}</span>
                </div>
              
              <div className="border-t border-gray-600 pt-3 mt-3 space-y-3">
                {/* CPU Usage */}
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-gray-400">CPUs:</span>
                    <span className="text-white text-xs">
                      {clusterStats.resources?.cpus?.used?.toFixed(1) || '0.0'} / {clusterStats.resources?.cpus?.total || 0}
                    </span>
                  </div>
                  <div className="w-full bg-gray-600 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${getResourceColor(getResourcePercentage(clusterStats.resources?.cpus?.used || 0, clusterStats.resources?.cpus?.total || 1))}`}
                      style={{ width: `${getResourcePercentage(clusterStats.resources?.cpus?.used || 0, clusterStats.resources?.cpus?.total || 1)}%` }}
                     />
                  </div>
                </div>

                {/* GPU Usage */}
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-gray-400">GPUs:</span>
                    <span className="text-white text-xs">
                      {clusterStats.resources?.gpus?.used?.toFixed(1) || '0.0'} / {clusterStats.resources?.gpus?.total || 0}
                    </span>
                  </div>
                  <div className="w-full bg-gray-600 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${getResourceColor(getResourcePercentage(clusterStats.resources?.gpus?.used || 0, clusterStats.resources?.gpus?.total || 1))}`}
                      style={{ width: `${getResourcePercentage(clusterStats.resources?.gpus?.used || 0, clusterStats.resources?.gpus?.total || 1)}%` }}
                     />
                  </div>
                </div>

                {/* Memory Usage */}
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-gray-400">Memory:</span>
                    <span className="text-white text-xs">
                      {clusterStats.resources?.memory_gb?.used?.toFixed(1) || '0.0'} / {clusterStats.resources?.memory_gb?.total || 0} GB
                    </span>
                  </div>
                  <div className="w-full bg-gray-600 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${getResourceColor(getResourcePercentage(clusterStats.resources?.memory_gb?.used || 0, clusterStats.resources?.memory_gb?.total || 1))}`}
                      style={{ width: `${getResourcePercentage(clusterStats.resources?.memory_gb?.used || 0, clusterStats.resources?.memory_gb?.total || 1)}%` }}
                     />
                  </div>
                </div>
              </div>

              <div className="border-t border-gray-600 pt-3 mt-3 space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">Active Jobs:</span>
                  <span className="text-yellow-400 font-semibold">{clusterStats.jobs?.active || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Completed:</span>
                  <span className="text-green-400 font-semibold">{clusterStats.jobs?.completed || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Failed:</span>
                  <span className="text-red-400 font-semibold">{clusterStats.jobs?.failed || 0}</span>
                </div>
              </div>
              </div>
            ) : (
              <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-3 text-center">
                <div className="text-red-400 text-sm">
                  ❌ Ray Cluster not connected
                </div>
                {clusterStats.error && (
                  <div className="text-xs text-red-300 mt-2">
                    {clusterStats.error}
                  </div>
                )}
              </div>
            )
          ) : (
            <div className="text-center text-gray-400">Loading...</div>
          )}
        </div>
      </div>

      {/* Active Jobs */}
      {activeJobs.length > 0 && (
        <div className="bg-gray-700/50 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-yellow-400 mb-3 flex items-center space-x-2">
            <span>⚙️</span>
            <span>Active Jobs ({activeJobs.length})</span>
          </h3>
          
          <div className="space-y-2">
            {activeJobs.map((job) => (
              <div key={job.job_id} className="bg-gray-800 rounded p-3 space-y-1">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-white font-mono text-sm">{job.job_id}</span>
                    <div className="flex items-center space-x-2 mt-1">
                      <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs font-semibold">
                        {job.role}
                      </span>
                      <span className="text-gray-400 text-xs">{job.task_id}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded text-xs font-semibold">
                      {job.status}
                    </div>
                    <div className="text-gray-400 text-xs mt-1">
                      {job.runtime}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeJobs.length === 0 && (
        <div className="bg-gray-700/50 rounded-lg p-4 text-center text-gray-400">
          <span>💤</span>
          <span className="ml-2">No active jobs</span>
        </div>
      )}
    </div>
  );
};

