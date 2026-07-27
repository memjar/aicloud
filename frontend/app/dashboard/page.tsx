import Link from 'next/link';

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="text-xl font-bold">Dashboard</div>
          <div className="flex gap-4">
            <button className="px-4 py-2 text-slate-300 hover:text-white transition">Settings</button>
            <button className="px-4 py-2 text-slate-300 hover:text-white transition">Sign Out</button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Welcome */}
        <div className="mb-12">
          <h1 className="text-4xl font-bold mb-4">Welcome back!</h1>
          <p className="text-slate-400">Manage your models, monitor usage, and control your inference platform.</p>
        </div>

        {/* Stats Grid */}
        <div className="grid md:grid-cols-4 gap-6 mb-12">
          {[
            { label: 'API Calls (30d)', value: '2.4M', trend: '+12%' },
            { label: 'Active Models', value: '8', trend: 'Stable' },
            { label: 'Avg Latency', value: '45ms', trend: '-8%' },
            { label: 'Cost (30d)', value: '$1,245', trend: '+5%' },
          ].map((stat, i) => (
            <div key={i} className="border border-slate-800 rounded-lg p-6 bg-slate-900/50 hover:border-slate-600 transition">
              <div className="text-slate-400 text-sm mb-2">{stat.label}</div>
              <div className="text-3xl font-bold mb-2">{stat.value}</div>
              <div className={`text-sm ${stat.trend.includes('-') || stat.trend === 'Stable' ? 'text-green-400' : 'text-yellow-400'}`}>
                {stat.trend}
              </div>
            </div>
          ))}
        </div>

        {/* Main Grid */}
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Requests Chart */}
          <div className="lg:col-span-2 border border-slate-800 rounded-lg p-6 bg-slate-900/50">
            <h2 className="text-lg font-semibold mb-6">API Requests (Last 30 Days)</h2>
            <div className="h-64 bg-slate-800/50 rounded-lg flex items-center justify-center text-slate-500">
              <div className="text-center">
                <div className="text-6xl mb-2">📊</div>
                <p>Chart placeholder - integrate PostHog/Segment</p>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="space-y-4">
            <div className="border border-slate-800 rounded-lg p-6 bg-slate-900/50 hover:border-slate-600 transition cursor-pointer">
              <div className="text-2xl mb-2">🚀</div>
              <h3 className="font-semibold mb-1">Deploy New Model</h3>
              <p className="text-sm text-slate-400">Upload and deploy in minutes</p>
            </div>
            <div className="border border-slate-800 rounded-lg p-6 bg-slate-900/50 hover:border-slate-600 transition cursor-pointer">
              <div className="text-2xl mb-2">🔑</div>
              <h3 className="font-semibold mb-1">API Keys</h3>
              <p className="text-sm text-slate-400">Manage authentication</p>
            </div>
            <div className="border border-slate-800 rounded-lg p-6 bg-slate-900/50 hover:border-slate-600 transition cursor-pointer">
              <div className="text-2xl mb-2">📖</div>
              <h3 className="font-semibold mb-1">API Docs</h3>
              <p className="text-sm text-slate-400">View documentation</p>
            </div>
            <div className="border border-slate-800 rounded-lg p-6 bg-slate-900/50 hover:border-slate-600 transition cursor-pointer">
              <div className="text-2xl mb-2">⚙️</div>
              <h3 className="font-semibold mb-1">Webhooks</h3>
              <p className="text-sm text-slate-400">Setup event notifications</p>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="mt-12 border border-slate-800 rounded-lg p-6 bg-slate-900/50">
          <h2 className="text-lg font-semibold mb-6">Recent Activity</h2>
          <div className="space-y-4">
            {[
              { event: 'Model deployed', model: 'gpt-4-turbo', time: '2 hours ago', status: '✓' },
              { event: 'API key created', model: 'sk-...', time: '1 day ago', status: '✓' },
              { event: 'Rate limit increased', model: 'default', time: '3 days ago', status: '✓' },
            ].map((item, i) => (
              <div key={i} className="flex justify-between items-center py-3 border-b border-slate-700 last:border-0">
                <div>
                  <div className="font-medium">{item.event}</div>
                  <div className="text-sm text-slate-400">{item.model}</div>
                </div>
                <div className="text-sm text-slate-400">{item.time}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
