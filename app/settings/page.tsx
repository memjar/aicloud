'use client';

import Link from 'next/link';
import { useBillingInfo } from '@/lib/hooks';
import { ErrorAlert } from '@/components/ErrorBoundary';
import { LoadingCard } from '@/components/Spinner';

export default function Settings() {
  const { data: billing, loading: billingLoading, error: billingError } = useBillingInfo();

  const formatCurrency = (num: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(num);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="text-slate-400 hover:text-white transition">
              Dashboard
            </Link>
            <span className="text-slate-600">/</span>
            <h1 className="text-2xl font-bold">Settings</h1>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid lg:grid-cols-4 gap-8">
          {/* Sidebar */}
          <div className="lg:col-span-1">
            <div className="space-y-2">
              {[
                { name: 'API Keys', href: '/settings/api-keys', icon: '🔑' },
                { name: 'Billing', href: '/settings/billing', icon: '💳' },
                { name: 'Team', href: '/settings/team', icon: '👥' },
                { name: 'Security', href: '/settings/security', icon: '🔒' },
              ].map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="block px-4 py-3 rounded-lg text-slate-300 hover:bg-slate-800 transition group"
                >
                  <span className="mr-2">{item.icon}</span>
                  {item.name}
                </Link>
              ))}
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3 space-y-8">
            {/* Account Section */}
            <div className="border border-slate-800 rounded-lg p-8 bg-slate-900/50">
              <h2 className="text-2xl font-bold mb-2">Account Settings</h2>
              <p className="text-slate-400 mb-6">Manage your account preferences and information</p>

              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium mb-2">Email Address</label>
                  <input
                    type="email"
                    defaultValue="user@example.com"
                    disabled
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-400 outline-none"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">Display Name</label>
                  <input
                    type="text"
                    defaultValue="Your Name"
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:border-blue-500 outline-none transition"
                  />
                </div>

                <button className="px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold transition">
                  Save Changes
                </button>
              </div>
            </div>

            {/* Billing Section */}
            <div className="border border-slate-800 rounded-lg p-8 bg-slate-900/50">
              <h2 className="text-2xl font-bold mb-2">Billing Information</h2>
              <p className="text-slate-400 mb-6">View and manage your billing</p>

              {billingError && <ErrorAlert error={billingError} />}

              {billingLoading ? (
                <LoadingCard />
              ) : billing ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-sm text-slate-400 mb-1">Current Plan</div>
                      <div className="text-lg font-semibold capitalize">{billing.planType}</div>
                    </div>
                    <div>
                      <div className="text-sm text-slate-400 mb-1">Monthly Cost</div>
                      <div className="text-lg font-semibold">{formatCurrency(billing.costThisMonth)}</div>
                    </div>
                  </div>

                  <div className="bg-slate-800/50 p-4 rounded-lg">
                    <p className="text-sm text-slate-400">
                      Next billing date: <span className="text-slate-300 font-medium">{new Date(billing.nextBillingDate).toLocaleDateString()}</span>
                    </p>
                  </div>

                  <Link
                    href="/settings/billing"
                    className="inline-block px-6 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold transition"
                  >
                    Manage Billing
                  </Link>
                </div>
              ) : null}
            </div>

            {/* Danger Zone */}
            <div className="border border-red-900/50 rounded-lg p-8 bg-red-950/20">
              <h2 className="text-2xl font-bold mb-2 text-red-400">Danger Zone</h2>
              <p className="text-slate-400 mb-6">Irreversible actions</p>

              <button className="px-6 py-2 bg-red-600 hover:bg-red-700 rounded-lg font-semibold transition">
                Delete Account
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
