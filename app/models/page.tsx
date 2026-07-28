'use client';

import { useModels } from '@/lib/hooks';
import { ErrorAlert } from '@/components/ErrorBoundary';
import { LoadingGrid } from '@/components/Spinner';

export default function Models() {
  const { data: models, loading, error } = useModels();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <h1 className="text-2xl font-bold">Available Models</h1>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {error && <ErrorAlert error={error} title="Failed to load models" />}

        <div className="mb-8 flex justify-between items-center">
          <div>
            <p className="text-slate-400">
              {loading ? 'Loading models...' : `${models?.length || 0} models available`}
            </p>
          </div>
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition">
            Upload Custom Model
          </button>
        </div>

        {/* Models Grid */}
        {loading ? (
          <LoadingGrid count={6} />
        ) : models && models.length > 0 ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {models.map((model) => (
              <div
                key={model.id}
                className="border border-slate-800 rounded-lg p-6 bg-slate-900/50 hover:border-slate-600 transition cursor-pointer group"
              >
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="font-semibold text-lg group-hover:text-blue-400 transition">
                      {model.name}
                    </h3>
                    <p className="text-sm text-slate-400">{model.provider}</p>
                  </div>
                  <div
                    className={`text-xs px-2 py-1 rounded ${
                      model.status === 'Available'
                        ? 'bg-green-900/50 text-green-300'
                        : model.status === 'Running'
                        ? 'bg-blue-900/50 text-blue-300'
                        : 'bg-red-900/50 text-red-300'
                    }`}
                  >
                    {model.status}
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4 py-4 border-t border-b border-slate-700">
                  <div>
                    <div className="text-xs text-slate-400">Type</div>
                    <div className="font-mono text-sm">{model.type}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400">Cost / 1k</div>
                    <div className="font-mono text-sm text-yellow-400">{model.costPer1k}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-400">Latency</div>
                    <div className="font-mono text-sm">{model.latency}</div>
                  </div>
                </div>

                {model.description && (
                  <p className="text-sm text-slate-400 mt-4">{model.description}</p>
                )}

                <button className="w-full mt-4 py-2 border border-slate-600 hover:border-blue-400 rounded transition text-sm font-medium">
                  View Details
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📦</div>
            <p className="text-slate-400">No models available</p>
          </div>
        )}
      </div>
    </div>
  );
}
