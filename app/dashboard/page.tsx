'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useUsageStats, useBillingInfo } from '@/lib/hooks';
import { ErrorAlert } from '@/components/ErrorBoundary';
import { LoadingCard, Spinner } from '@/components/Spinner';

export default function Dashboard() {
  const { data: stats, loading: statsLoading, error: statsError } = useUsageStats();
  const { data: billing, loading: billingLoading, error: billingError } = useBillingInfo();
  const [showApiKeyAlert] = useState(false);

  const formatNumber = (num: number) => new Intl.NumberFormat('en-US').format(num);
  const formatCurrency = (num: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(num);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="text-xl font-bold">Dashboard</div>
          <div className="flex gap-4">
            <Link
              href="/settings"
              className="px-4 py-2 text-slate-300 hover:text-white transition"
            >
              Settings
            </Link>
            <button className="px-4 py-2 text-slate-300 hover:text-white transition">
              Sign Out
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {statsError && <ErrorAlert error={statsError} title="Failed to load usage stats" />}
        {billingError && <ErrorAlert error={billingError} title="Failed to load billing info" />}

        <div className="mb-12">
          <h1 className="text-4xl font-bold mb-4">Welcome back!</h1>
          <p className="text-slate-400">Manage your models, monitor usage, and control your inference platform.</p>
        </div>

        {/* Stats Grid */}
        <div className="grid md:grid-cols-4 gap-6 mb-12">
          {statsLoading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <LoadingCard key={i} />
            ))
          ) : stats ? (
            [
              { label: 'API Calls (30d)', value: formatNumber(stats.apiCalls30d), trend: stats.trend.apiCalls },
              { label: 'Active Models', value: stats.activeModels.toString(), trend: 'Stable' },
              { label: 'Avg Latency', value: `${stats.avgLatency}ms`, trend: stats.trend.latency },
              { label: 'Cost (30d)', value: formatCurrency(stats.cost30d), trend: stats.trend.cost },
            ].map((stat, i) => (
              <div key={i} className="border border-slate-800 rounded-lg p-6 bg-slate-900/50 hover:border-slate-600 transition">
                <div className="text-slate-400 text-sm mb-2">{stat.label}</div>
                <div className="text-3xl font-bold mb-2">{stat.value}</div>
                <div className={`text-sm ${stat.trend.includes('-') || stat.trend === 'Stable' ? 'text-green-400' : 'text-yellow-400'}`}>
                  {stat.trend}
                </div>
              </div>
            ))
          ) : null}
        </div>

        {/* Main Grid */}
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Chart Placeholder */}
          <div className="lg:col-span-2 border border-slate-800 rounded-lg p-6 bg-slate-900/50">
            <h2 className="text-lg font-semibold mb-6">API Requests (Last 30 Days)</h2>
            <div className="h-64 bg-slate-800/50 rounded-lg flex items-center justify-center text-slate-500">
              <div className="text-center">
                <div className="text-6xl mb-2">📊</div>
                <p>Chart - integrate with analytics service</p>
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="space-y-4">
            <Link
              href="/playground"
              className="border border-slate-800 rounded-lg p-6 bg-slate-900/50 hover:border-slate-600 transition cursor-pointer block"
            >
              <div className="text-2xl mb-2">🚀</div>
              <h3 className="font-semibold mb-1">Try API</h3>
              <p className="text-sm text-slate-400">Test in playground</p>
            </Link>

            <Link
              href="/settings/api-keys"
              className="border border-slate-800 rounded-lg p-6 bg-slate-900/50 hover:border-slate-600 transition cursor-pointer block"
            >
              <div className="text-2xl mb-2">🔑</div>
              <h3 className="font-semibold mb-1">API Keys</h3>
              <p className="text-sm text-slate-400">Manage authentication</p>
            </Link>

            <a
              href="/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="border border-slate-800 rounded-lg p-6 bg-slate-900/50 hover:border-slate-600 transition cursor-pointer block"
            >
              <div className="text-2xl mb-2">📖</div>
              <h3 className="font-semibold mb-1">API Docs</h3>
              <p className="text-sm text-slate-400">View documentation</p>
            </a>

            <div className="border border-slate-800 rounded-lg p-6 bg-slate-900/50 hover:border-slate-600 transition cursor-pointer">
              <div className="text-2xl mb-2">⚙️</div>
              <h3 className="font-semibold mb-1">Webhooks</h3>
              <p className="text-sm text-slate-400">Setup notifications</p>
            </div>
          </div>
        </div>

        {/* Billing Section */}
        {billing && (
          <div className="mt-12 border border-slate-800 rounded-lg p-6 bg-slate-900/50">
            <h2 className="text-lg font-semibold mb-6">Billing Overview</h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div>
                <div className="text-sm text-slate-400 mb-1">Plan Type</div>
                <div className="text-xl font-semibold capitalize">{billing.planType}</div>
              </div>
              <div>
                <div className="text-sm text-slate-400 mb-1">Current Usage</div>
                <div className="text-xl font-semibold">{formatNumber(billing.currentUsage)} calls</div>
              </div>
              <div>
                <div className="text-sm text-slate-400 mb-1">Total Tokens</div>
                <div className="text-xl font-semibold">{formatNumber(billing.totalTokens)}</div>
              </div>
              <div>
                <div className="text-sm text-slate-400 mb-1">Cost This Month</div>
                <div className="text-xl font-semibold text-yellow-400">{formatCurrency(billing.costThisMonth)}</div>
              </div>
            </div>
            <div className="mt-6 pt-6 border-t border-slate-700">
              <p className="text-sm text-slate-400">
                Next billing date: <span className="text-slate-300 font-medium">{new Date(billing.nextBillingDate).toLocaleDateString()}</span>
              </p>
            </div>
          </div>
        )}

        {/* Recent Activity */}
        <div className="mt-12 border border-slate-800 rounded-lg p-6 bg-slate-900/50">
          <h2 className="text-lg font-semibold mb-6">Recent Activity</h2>
          <div className="space-y-4">
            {[
              { event: 'Model deployment', model: 'gpt-4-turbo', time: '2 hours ago', status: '✓' },
              { event: 'API request', model: 'claude-3-opus', time: '1 hour ago', status: '✓' },
              { event: 'Rate limit adjusted', model: 'default', time: '3 days ago', status: '✓' },
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
