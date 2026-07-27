import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'aimodel.cloud - AI Inference Platform',
  description: 'Deploy, manage, and monetize AI models. White-label inference at scale.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white">
          {children}
        </div>
      </body>
    </html>
  );
}
