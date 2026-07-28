'use client';

import { useState } from 'react';
import { useCompletion, useModels } from '@/lib/hooks';
import { ErrorAlertWithRetry } from '@/components/ErrorBoundary';
import { Spinner, LoadingGrid } from '@/components/Spinner';

export default function Playground() {
  const [model, setModel] = useState('gpt-4-turbo');
  const [prompt, setPrompt] = useState('Explain quantum computing in simple terms.');
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(1000);
  const [responseError, setResponseError] = useState(false);

  const { data: completion, loading: completionLoading, error: completionError, submit } = useCompletion();
  const { data: models, loading: modelsLoading, error: modelsError } = useModels();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setResponseError(false);
    try {
      await submit(prompt, model, maxTokens, temperature);
    } catch {
      setResponseError(true);
    }
  };

  const responseText = completion?.choices[0]?.text || '';
  const hasApiKey = typeof window !== 'undefined' && localStorage.getItem('apiKey');

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <h1 className="text-2xl font-bold">API Playground</h1>
          <p className="text-slate-400">Test models in real-time</p>
          {!hasApiKey && (
            <p className="text-sm text-yellow-400 mt-2">
              ⚠️ No API key found. <a href="/settings/api-keys" className="underline hover:text-yellow-300">Add one in settings</a>
            </p>
          )}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {completionError && (
          <ErrorAlertWithRetry
            error={completionError}
            onDismiss={() => setResponseError(false)}
            onRetry={handleSubmit}
            isLoading={completionLoading}
          />
        )}

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Input */}
          <div>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-2">Model</label>
                {modelsLoading ? (
                  <div className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-400">
                    Loading models...
                  </div>
                ) : (
                  <select
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    disabled={completionLoading}
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:border-blue-500 outline-none transition disabled:opacity-50"
                  >
                    {models?.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} ({m.provider})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Prompt</label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  disabled={completionLoading}
                  rows={10}
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:border-blue-500 outline-none transition font-mono text-sm disabled:opacity-50"
                  placeholder="Enter your prompt..."
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Temperature: {temperature.toFixed(1)}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    value={temperature}
                    onChange={(e) => setTemperature(parseFloat(e.target.value))}
                    disabled={completionLoading}
                    className="w-full disabled:opacity-50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Max Tokens</label>
                  <input
                    type="number"
                    value={maxTokens}
                    onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                    disabled={completionLoading}
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:border-blue-500 outline-none transition disabled:opacity-50"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={completionLoading || !hasApiKey}
                className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 rounded-lg font-semibold transition"
              >
                {completionLoading ? 'Inferring...' : 'Send Request'}
              </button>
            </form>
          </div>

          {/* Output */}
          <div>
            <div className="border border-slate-800 rounded-lg p-6 bg-slate-900/50 h-full">
              <h2 className="text-lg font-semibold mb-4">Response</h2>
              {completionLoading ? (
                <div className="flex items-center justify-center h-64">
                  <Spinner />
                </div>
              ) : responseText ? (
                <div>
                  <div className="bg-slate-800/50 p-4 rounded-lg font-mono text-sm whitespace-pre-wrap text-slate-200 max-h-96 overflow-y-auto mb-4">
                    {responseText}
                  </div>
                  {completion && (
                    <div className="grid grid-cols-3 gap-2 text-xs text-slate-400">
                      <div>
                        <div className="text-slate-500">Input Tokens</div>
                        <div className="font-mono">{completion.usage.prompt_tokens}</div>
                      </div>
                      <div>
                        <div className="text-slate-500">Output Tokens</div>
                        <div className="font-mono">{completion.usage.completion_tokens}</div>
                      </div>
                      <div>
                        <div className="text-slate-500">Total Tokens</div>
                        <div className="font-mono">{completion.usage.total_tokens}</div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-center h-64 text-slate-500">
                  <div className="text-center">
                    <div className="text-4xl mb-2">🤖</div>
                    <p>Response will appear here</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Code Examples */}
        <div className="mt-12">
          <h2 className="text-2xl font-bold mb-6">Example Requests</h2>
          <div className="grid md:grid-cols-2 gap-6">
            {[
              {
                lang: 'curl',
                code: `curl https://api.aimodels.cloud/v1/completions \\
  -H "Authorization: Bearer sk-..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gpt-4-turbo",
    "prompt": "Hello, world!",
    "max_tokens": 100
  }'`,
              },
              {
                lang: 'python',
                code: `import requests

response = requests.post(
    "https://api.aimodels.cloud/v1/completions",
    headers={"Authorization": "Bearer sk-..."},
    json={
        "model": "gpt-4-turbo",
        "prompt": "Hello, world!",
        "max_tokens": 100
    }
)

print(response.json())`,
              },
            ].map((example, i) => (
              <div key={i} className="border border-slate-800 rounded-lg p-6 bg-slate-900/50">
                <div className="text-sm font-mono text-blue-400 mb-3">{example.lang}</div>
                <pre className="text-xs overflow-x-auto text-slate-300">{example.code}</pre>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
