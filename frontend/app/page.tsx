import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen">
      {/* Navigation */}
      <nav className="border-b border-slate-800 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
            aimodel.cloud
          </div>
          <div className="flex gap-8 items-center">
            <Link href="/docs" className="text-slate-300 hover:text-white transition">API Docs</Link>
            <Link href="/models" className="text-slate-300 hover:text-white transition">Models</Link>
            <Link href="/dashboard" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition">
              Sign In
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="text-center mb-16">
          <h1 className="text-6xl font-bold mb-6 leading-tight">
            Inference is everything
          </h1>
          <p className="text-xl text-slate-300 mb-8 max-w-2xl mx-auto">
            Deploy any model. Scale instantly. Monetize reliably. The platform powering the next generation of AI applications.
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/signup" className="px-8 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-semibold transition">
              Get Started Free
            </Link>
            <Link href="/docs" className="px-8 py-3 border border-slate-600 hover:border-slate-400 rounded-lg font-semibold transition">
              API Reference
            </Link>
          </div>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-3 gap-8 mt-20">
          {[
            {
              title: 'Deploy in Minutes',
              description: 'Push any model to production. We handle infrastructure, scaling, and monitoring.',
              icon: '🚀',
            },
            {
              title: 'Multi-Model Gateway',
              description: 'Route requests across OpenAI, Anthropic, or your own fine-tuned models.',
              icon: '🔄',
            },
            {
              title: 'White-Label Ready',
              description: 'Embed inference into your platform. Your domain, your pricing, your brand.',
              icon: '🏷️',
            },
            {
              title: 'Global Performance',
              description: 'Inference globally distributed with sub-100ms latency from anywhere.',
              icon: '🌍',
            },
            {
              title: 'Developer Experience',
              description: 'Dead-simple REST API. Full SDKs. Comprehensive logging and analytics.',
              icon: '⚡',
            },
            {
              title: 'Cost Control',
              description: 'Pay for what you use. Set quotas. Monitor spend in real-time.',
              icon: '💰',
            },
          ].map((feature, i) => (
            <div key={i} className="border border-slate-800 rounded-lg p-6 hover:border-slate-600 transition bg-slate-900/50">
              <div className="text-4xl mb-4">{feature.icon}</div>
              <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
              <p className="text-slate-400">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing Preview */}
      <section className="bg-slate-900/50 border-y border-slate-800 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl font-bold mb-4">Simple, Transparent Pricing</h2>
          <p className="text-slate-300 mb-12">Pay only for inference. No setup fees. Cancel anytime.</p>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              { name: 'Starter', price: '$0', requests: 'Up to 10k req/mo', features: ['Public API', 'Community Support'] },
              { name: 'Pro', price: '$29', requests: '1M req/mo included', features: ['Priority Support', 'Custom Models', 'Analytics', 'Webhooks'] },
              { name: 'Enterprise', price: 'Custom', requests: 'Unlimited', features: ['Dedicated Infra', 'SLA', 'White-Label', 'Custom Integration'] },
            ].map((tier, i) => (
              <div key={i} className={`border rounded-lg p-8 transition ${i === 1 ? 'border-blue-500 bg-blue-950/30 scale-105' : 'border-slate-700 bg-slate-900/50'}`}>
                <h3 className="text-2xl font-bold mb-2">{tier.name}</h3>
                <div className="text-4xl font-bold text-blue-400 mb-2">{tier.price}</div>
                <div className="text-sm text-slate-400 mb-6">{tier.requests}</div>
                <button className={`w-full py-2 rounded-lg mb-6 transition ${i === 1 ? 'bg-blue-600 hover:bg-blue-700' : 'border border-slate-600 hover:border-slate-400'}`}>
                  Get Started
                </button>
                <div className="text-left space-y-2">
                  {tier.features.map((f, j) => (
                    <div key={j} className="text-sm text-slate-300">✓ {f}</div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="font-bold mb-4">Product</div>
              <div className="space-y-2 text-sm text-slate-400">
                <div><Link href="/pricing">Pricing</Link></div>
                <div><Link href="/models">Models</Link></div>
                <div><Link href="/docs">Documentation</Link></div>
              </div>
            </div>
            <div>
              <div className="font-bold mb-4">Company</div>
              <div className="space-y-2 text-sm text-slate-400">
                <div><Link href="/about">About</Link></div>
                <div><Link href="/blog">Blog</Link></div>
                <div><Link href="/careers">Careers</Link></div>
              </div>
            </div>
            <div>
              <div className="font-bold mb-4">Legal</div>
              <div className="space-y-2 text-sm text-slate-400">
                <div><Link href="/privacy">Privacy</Link></div>
                <div><Link href="/terms">Terms</Link></div>
              </div>
            </div>
            <div>
              <div className="font-bold mb-4">Connect</div>
              <div className="space-y-2 text-sm text-slate-400">
                <div><Link href="https://twitter.com">Twitter</Link></div>
                <div><Link href="https://github.com">GitHub</Link></div>
              </div>
            </div>
          </div>
          <div className="border-t border-slate-800 pt-8 text-center text-slate-500 text-sm">
            © 2025 aimodel.cloud. Inference, simplified.
          </div>
        </div>
      </footer>
    </main>
  );
}
