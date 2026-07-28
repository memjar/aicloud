'use client';

import { ReactNode } from 'react';
import { ApiError } from '@/lib/api';

interface ErrorProps {
  error: ApiError | null;
  onDismiss?: () => void;
  title?: string;
}

export function ErrorAlert({ error, onDismiss, title = 'Error' }: ErrorProps) {
  if (!error) return null;

  return (
    <div className="bg-red-900/20 border border-red-700 rounded-lg p-4 mb-6">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-semibold text-red-400">{title}</h3>
          <p className="text-sm text-red-300 mt-1">{error.message}</p>
          {error.code && <p className="text-xs text-red-300/70 mt-1">Code: {error.code}</p>}
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-red-400 hover:text-red-300 transition"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
}

interface ErrorRetryProps extends ErrorProps {
  onRetry?: () => void;
  isLoading?: boolean;
}

export function ErrorAlertWithRetry({
  error,
  onDismiss,
  onRetry,
  isLoading,
  title = 'Error',
}: ErrorRetryProps) {
  if (!error) return null;

  return (
    <div className="bg-red-900/20 border border-red-700 rounded-lg p-4 mb-6">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <h3 className="font-semibold text-red-400">{title}</h3>
          <p className="text-sm text-red-300 mt-1">{error.message}</p>
          {error.code && <p className="text-xs text-red-300/70 mt-1">Code: {error.code}</p>}
          {onRetry && (
            <button
              onClick={onRetry}
              disabled={isLoading}
              className="text-sm text-red-400 hover:text-red-300 mt-3 transition disabled:opacity-50"
            >
              {isLoading ? 'Retrying...' : 'Try Again'}
            </button>
          )}
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-red-400 hover:text-red-300 transition ml-4"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
}

export function FallbackError({ message = 'Something went wrong' }: { message?: string }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
      <div className="text-center max-w-md">
        <div className="text-6xl mb-4">⚠️</div>
        <h1 className="text-2xl font-bold mb-2">Error</h1>
        <p className="text-slate-400 mb-6">{message}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition"
        >
          Reload Page
        </button>
      </div>
    </div>
  );
}
