'use client';

import { useState } from 'react';

export default function Playground() {
  const [model, setModel] = useState('gpt-4-turbo');
  const [prompt, setPrompt] = useState('Explain quantum computing in simple terms.');
  const [response, setResponse] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const res = await fetch('/api/infer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model, prompt }),
      });

      const data = await res.json();
      setResponse(data.result || 'No response');
    } catch (error) {
      setResponse(`Error: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <h1 className="text-2xl font-bold">API Playground</h1>
          <p className="text-slate-400">Test models in real-time</p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Input */}
          <div>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-sm font-medium mb-2">Model</label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:border-blue-500 outline-none transition"
                >
                  <option value="gpt-4-turbo">GPT-4 Turbo</option>
                  <option value="claude-3-opus">Claude 3 Opus</option>
                  <option value="llama-2-70b">Llama 2 70B</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Prompt</label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  rows={10}
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:border-blue-500 outline-none transition font-mono text-sm"
                  placeholder="Enter your prompt..."
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Temperature</label>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    defaultValue="0.7"
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Max Tokens</label>
                  <input
                    type="number"
                    defaultValue="1000"
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:border-blue-500 outline-none transition"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 rounded-lg font-semibold transition"
              >
                {loading ? 'Inferring...' : 'Send Request'}
              </button>
            </form>
          </div>

          {/* Output */}
          <div>
            <div className="border border-slate-800 rounded-lg p-6 bg-slate-900/50 h-full">
              <h2 className="text-lg font-semibold mb-4">Response</h2>
              {response ? (
                <div className="bg-slate-800/50 p-4 rounded-lg font-mono text-sm whitespace-pre-wrap text-slate-200 max-h-96 overflow-y-auto">
                  {response}
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
                code: `curl https://api.aimodel.cloud/v1/infer \\
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
    "https://api.aimodel.cloud/v1/infer",
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
