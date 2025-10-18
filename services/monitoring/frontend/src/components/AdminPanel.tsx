import { useState } from 'react';
import { Trash2, StopCircle, PlayCircle, AlertTriangle } from 'lucide-react';

export function AdminPanel() {
  const [loading, setLoading] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const executeAction = async (action: string, endpoint: string, confirmMessage: string) => {
    if (!confirm(confirmMessage)) {
      return;
    }

    setLoading(action);
    setLastResult(null);

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (data.status === 'success') {
        setLastResult({ type: 'success', message: data.message });
      } else {
        setLastResult({ type: 'error', message: data.message || 'Operation failed' });
      }
    } catch (error) {
      setLastResult({ type: 'error', message: `Failed to execute ${action}: ${error}` });
    } finally {
      setLoading(null);
    }
  };

  const executeTestCase = async (testCase: 'basic' | 'medium' | 'complex') => {
    const descriptions = {
      basic: 'Add login button to homepage (2h)',
      medium: 'Implement user authentication system (8h)',
      complex: 'Build real-time collaborative editing system (40h)',
    };

    if (!confirm(`Execute test case: ${descriptions[testCase]}?`)) {
      return;
    }

    setLoading(`test-${testCase}`);
    setLastResult(null);

    try {
      const response = await fetch(`/api/admin/test-cases/execute?test_case=${testCase}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (data.status === 'success') {
        setLastResult({ 
          type: 'success', 
          message: `${data.message}\nStory ID: ${data.story_id}` 
        });
      } else {
        setLastResult({ type: 'error', message: data.message || 'Test case execution failed' });
      }
    } catch (error) {
      setLastResult({ type: 'error', message: `Failed to execute test case: ${error}` });
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
          ⚙️ Admin Control Panel
        </h2>
        <div className="text-sm text-yellow-400 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          Danger Zone
        </div>
      </div>

      {/* Last Result Banner */}
      {lastResult && (
        <div
          className={`mb-6 p-4 rounded-lg border ${
            lastResult.type === 'success'
              ? 'bg-green-500/10 border-green-500/50 text-green-400'
              : 'bg-red-500/10 border-red-500/50 text-red-400'
          }`}
        >
          <div className="font-semibold mb-1">
            {lastResult.type === 'success' ? '✅ Success' : '❌ Error'}
          </div>
          <div className="text-sm whitespace-pre-line">{lastResult.message}</div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Data Cleanup Section */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-white border-b border-gray-700 pb-2">
            🗑️ Data Cleanup
          </h3>

          <button
            onClick={() =>
              executeAction(
                'clear-nats',
                '/api/admin/nats/clear',
                '⚠️  Clear all NATS JetStream streams?\n\nThis will delete all queued messages and stream data.'
              )
            }
            disabled={loading !== null}
            className="w-full flex items-center gap-3 px-4 py-3 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Trash2 className="w-5 h-5" />
            <div className="text-left flex-1">
              <div className="font-semibold">Clear NATS Streams</div>
              <div className="text-xs text-red-300">Delete all JetStream data</div>
            </div>
            {loading === 'clear-nats' && (
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-red-400" />
            )}
          </button>

          <button
            onClick={() =>
              executeAction(
                'clear-valkey',
                '/api/admin/valkey/clear',
                '⚠️  Clear all ValKey cache data?\n\nThis will delete all cached data.'
              )
            }
            disabled={loading !== null}
            className="w-full flex items-center gap-3 px-4 py-3 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Trash2 className="w-5 h-5" />
            <div className="text-left flex-1">
              <div className="font-semibold">Clear ValKey Cache</div>
              <div className="text-xs text-red-300">Flush all cached data</div>
            </div>
            {loading === 'clear-valkey' && (
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-red-400" />
            )}
          </button>

          <button
            onClick={() =>
              executeAction(
                'clear-neo4j',
                '/api/admin/neo4j/clear',
                '⚠️  Clear all Neo4j graph data?\n\nThis will delete ALL nodes and relationships permanently!'
              )
            }
            disabled={loading !== null}
            className="w-full flex items-center gap-3 px-4 py-3 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Trash2 className="w-5 h-5" />
            <div className="text-left flex-1">
              <div className="font-semibold">Clear Neo4j Graph</div>
              <div className="text-xs text-red-300">Delete all nodes & relationships</div>
            </div>
            {loading === 'clear-neo4j' && (
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-red-400" />
            )}
          </button>

          <button
            onClick={() =>
              executeAction(
                'kill-ray-jobs',
                '/api/admin/ray/kill-jobs',
                '⚠️  Kill all active Ray jobs?\n\nThis will terminate all running deliberations.'
              )
            }
            disabled={loading !== null}
            className="w-full flex items-center gap-3 px-4 py-3 bg-orange-500/20 hover:bg-orange-500/30 text-orange-400 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <StopCircle className="w-5 h-5" />
            <div className="text-left flex-1">
              <div className="font-semibold">Kill Ray Jobs</div>
              <div className="text-xs text-orange-300">Terminate all active jobs</div>
            </div>
            {loading === 'kill-ray-jobs' && (
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-orange-400" />
            )}
          </button>
        </div>

        {/* Test Cases Section */}
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-white border-b border-gray-700 pb-2">
            🧪 Test Cases
          </h3>

          <button
            onClick={() => executeTestCase('basic')}
            disabled={loading !== null}
            className="w-full flex items-center gap-3 px-4 py-3 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <PlayCircle className="w-5 h-5" />
            <div className="text-left flex-1">
              <div className="font-semibold">Basic Test Case</div>
              <div className="text-xs text-blue-300">Add login button (2 hours)</div>
            </div>
            {loading === 'test-basic' && (
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-400" />
            )}
          </button>

          <button
            onClick={() => executeTestCase('medium')}
            disabled={loading !== null}
            className="w-full flex items-center gap-3 px-4 py-3 bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <PlayCircle className="w-5 h-5" />
            <div className="text-left flex-1">
              <div className="font-semibold">Medium Test Case</div>
              <div className="text-xs text-purple-300">User authentication system (8 hours)</div>
            </div>
            {loading === 'test-medium' && (
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-purple-400" />
            )}
          </button>

          <button
            onClick={() => executeTestCase('complex')}
            disabled={loading !== null}
            className="w-full flex items-center gap-3 px-4 py-3 bg-pink-500/20 hover:bg-pink-500/30 text-pink-400 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <PlayCircle className="w-5 h-5" />
            <div className="text-left flex-1">
              <div className="font-semibold">Complex Test Case</div>
              <div className="text-xs text-pink-300">Real-time collaborative editing (40 hours)</div>
            </div>
            {loading === 'test-complex' && (
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-pink-400" />
            )}
          </button>

          <div className="bg-gray-700/50 rounded-lg p-4 mt-4">
            <div className="text-sm text-gray-400">
              <p className="font-semibold text-white mb-2">📝 Test Case Flow:</p>
              <ol className="list-decimal list-inside space-y-1 text-xs">
                <li>Story created and sent to Planning Service</li>
                <li>Planning generates tasks and plan</li>
                <li>Orchestrator dispatches to agent councils</li>
                <li>Agents deliberate and execute tasks</li>
                <li>Results saved to Neo4j and ValKey</li>
              </ol>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

