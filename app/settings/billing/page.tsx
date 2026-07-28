'use client';

import Link from 'next/link';
import { useBillingInfo } from '@/lib/hooks';
import { ErrorAlert } from '@/components/ErrorBoundary';
import { LoadingCard } from '@/components/Spinner';

export default function BillingSettings() {
  const { data: billing, loading: billingLoading, error: billingError } = useBillingInfo();

  const formatCurrency = (num: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(num);

  const formatNumber = (num: number) => new Intl.NumberFormat('en-US').format(num);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-4">
            <Link href="/settings" className="text-slate-400 hover:text-white transition">
              Settings
            </Link>
            <span className="text-slate-600">/</span>
            <h1 className="text-2xl font-bold">Billing</h1>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {billingError && <ErrorAlert error={billingError} />}

        {billingLoading ? (
          <LoadingCard />
        ) : billing ? (
          <div className="space-y-8">
            {/* Current Plan */}
            <div className="border border-slate-800 rounded-lg p-8 bg-slate-900/50">
              <h2 className="text-2xl font-bold mb-6">Current Plan</h2>
              <div className="space-y-4">
                <div className="flex justify-between items-center pb-4 border-b border-slate-700">
                  <div>
                    <div className="font-semibold capitalize text-lg">{billing.planType} Plan</div>
                    <p className="text-slate-400">Billed monthly</p>
                  </div>
                  <div className="text-right">
                    <div className="text-3xl font-bold">{formatCurrency(billing.costThisMonth)}</div>
                    <p className="text-sm text-slate-400">this month</p>
                  </div>
                </div>

                <button className="px-6 py-2 border border-slate-600 hover:border-blue-400 rounded-lg transition">
                  Change Plan
                </button>
              </div>
            </div>

            {/* Usage Summary */}
            <div className="border border-slate-800 rounded-lg p-8 bg-slate-900/50">
              <h2 className="text-2xl font-bold mb-6">Usage Summary</h2>
              <div className="grid md:grid-cols-3 gap-6">
                <div>
                  <div className="text-sm text-slate-400 mb-2">API Calls This Month</div>
                  <div className="text-3xl font-bold">{formatNumber(billing.currentUsage)}</div>
                </div>
                <div>
                  <div className="text-sm text-slate-400 mb-2">Total Tokens Used</div>
                  <div className="text-3xl font-bold">{formatNumber(billing.totalTokens)}</div>
                </div>
                <div>
                  <div className="text-sm text-slate-400 mb-2">Avg Cost Per Call</div>
                  <div className="text-3xl font-bold">
                    {billing.currentUsage > 0
                      ? formatCurrency(billing.costThisMonth / billing.currentUsage)
                      : '$0.00'}
                  </div>
                </div>
              </div>
            </div>

            {/* Payment Method */}
            <div className="border border-slate-800 rounded-lg p-8 bg-slate-900/50">
              <h2 className="text-2xl font-bold mb-6">Payment Method</h2>
              <div className="space-y-4">
                <div className="bg-slate-800/50 p-4 rounded-lg">
                  <div className="flex justify-between items-center">
                    <div>
                      <div className="font-semibold">Visa •••• 4242</div>
                      <p className="text-sm text-slate-400">Expires 12/25</p>
                    </div>
                    <span className="text-green-400">✓ Active</span>
                  </div>
                </div>

                <button className="px-6 py-2 border border-slate-600 hover:border-blue-400 rounded-lg transition">
                  Update Payment Method
                </button>
              </div>
            </div>

            {/* Billing History */}
            <div className="border border-slate-800 rounded-lg p-8 bg-slate-900/50">
              <h2 className="text-2xl font-bold mb-6">Billing History</h2>
              <div className="space-y-3">
                {[
                  { date: 'Jul 1, 2024', amount: formatCurrency(125.50), status: 'Paid' },
                  { date: 'Jun 1, 2024', amount: formatCurrency(98.75), status: 'Paid' },
                  { date: 'May 1, 2024', amount: formatCurrency(112.30), status: 'Paid' },
                ].map((invoice, i) => (
                  <div key={i} className="flex justify-between items-center py-3 border-b border-slate-700 last:border-0">
                    <div>
                      <div className="font-medium">{invoice.date}</div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="font-semibold">{invoice.amount}</div>
                        <div className="text-xs text-green-400">{invoice.status}</div>
                      </div>
                      <button className="px-3 py-1 text-sm border border-slate-600 hover:border-slate-400 rounded transition">
                        Download
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Next Billing */}
            <div className="bg-blue-900/20 border border-blue-700 rounded-lg p-4">
              <p className="text-blue-300">
                Next billing date: <span className="font-semibold">{new Date(billing.nextBillingDate).toLocaleDateString()}</span>
              </p>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
