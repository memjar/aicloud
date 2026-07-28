'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useApiKeyManagement } from '@/lib/hooks';
import { ErrorAlertWithRetry } from '@/components/ErrorBoundary';
import { Spinner } from '@/components/Spinner';

export default function ApiKeysSettings() {
  const { keys, loading, error, creating, deleting, createKey, deleteKey } = useApiKeyManagement();
  const [keyName, setKeyName] = useState('');
  const [showNewKey, setShowNewKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyName.trim()) return;

    try {
      await createKey(keyName);
      setKeyName('');
    } catch (error) {
      console.error('Failed to create key:', error);
    }
  };

  const handleCopyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDeleteKey = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this API key? This action cannot be undone.')) {
      try {
        await deleteKey(id);
      } catch (error) {
        console.error('Failed to delete key:', error);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="text-slate-400 hover:text-white transition">
              Dashboard
            </Link>
            <span className="text-slate-600">/</span>
            <h1 className="text-2xl font-bold">API Keys</h1>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {error && (
          <ErrorAlertWithRetry
            error={error}
            title="Failed to load API keys"
          />
        )}

        {/* Create New Key */}
        <div className="border border-slate-800 rounded-lg p-8 bg-slate-900/50 mb-8">
          <h2 className="text-2xl font-bold mb-2">Create New API Key</h2>
          <p className="text-slate-400 mb-6">Generate a new API key for your application</p>

          <form onSubmit={handleCreateKey} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Key Name</label>
              <input
                type="text"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                placeholder="e.g., Production, Development, Testing"
                disabled={creating}
                className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:border-blue-500 outline-none transition disabled:opacity-50"
              />
              <p className="text-xs text-slate-400 mt-1">Choose a descriptive name to identify this key</p>
            </div>

            <button
              type="submit"
              disabled={creating || !keyName.trim()}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 rounded-lg font-semibold transition"
            >
              {creating ? 'Creating...' : 'Create API Key'}
            </button>
          </form>
        </div>

        {/* Existing Keys */}
        <div className="border border-slate-800 rounded-lg p-8 bg-slate-900/50">
          <h2 className="text-2xl font-bold mb-6">Your API Keys</h2>

          {loading ? (
            <div className="flex justify-center py-12">
              <Spinner />
            </div>
          ) : keys.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">🔑</div>
              <p className="text-slate-400 mb-4">No API keys yet</p>
              <p className="text-sm text-slate-500">Create one above to get started</p>
            </div>
          ) : (
            <div className="space-y-4">
              {keys.map((key) => (
                <div key={key.id} className="border border-slate-700 rounded-lg p-4 hover:border-slate-600 transition">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <h3 className="font-semibold flex items-center gap-2">
                        {key.name}
                        {key.isActive && (
                          <span className="text-xs px-2 py-1 rounded bg-green-900/50 text-green-300">
                            Active
                          </span>
                        )}
                      </h3>
                      <p className="text-sm text-slate-400">
                        Created {new Date(key.createdAt).toLocaleDateString()}
                      </p>
                      {key.lastUsed && (
                        <p className="text-sm text-slate-500">
                          Last used {new Date(key.lastUsed).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={() => handleDeleteKey(key.id)}
                      disabled={deleting === key.id}
                      className="px-3 py-1 text-sm text-red-400 hover:text-red-300 transition disabled:opacity-50"
                    >
                      {deleting === key.id ? 'Deleting...' : 'Delete'}
                    </button>
                  </div>

                  <div className="bg-slate-800/50 p-3 rounded-lg font-mono text-sm flex items-center justify-between">
                    <span className="text-slate-300 truncate">{key.key}</span>
                    <button
                      onClick={() => handleCopyKey(key.key)}
                      className="ml-2 px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 rounded transition whitespace-nowrap"
                    >
                      {copied ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Security Notice */}
        <div className="mt-8 bg-blue-900/20 border border-blue-700 rounded-lg p-4">
          <h3 className="font-semibold text-blue-400 mb-2">Security Notice</h3>
          <ul className="text-sm text-blue-300 space-y-1 list-disc list-inside">
            <li>Never share your API keys in public code or repositories</li>
            <li>Rotate keys regularly and delete unused ones</li>
            <li>Use different keys for development and production</li>
            <li>Store keys securely using environment variables</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
