'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiClient, ApiError, Model, UsageStats, ApiKey, BillingInfo } from './api';

interface UseAsyncState<T> {
  data: T | null;
  loading: boolean;
  error: ApiError | null;
}

function useAsync<T>(
  asyncFunction: () => Promise<T>,
  immediate = true
): UseAsyncState<T> & { refetch: () => Promise<void> } {
  const [state, setState] = useState<UseAsyncState<T>>({
    data: null,
    loading: immediate,
    error: null,
  });

  const execute = useCallback(async () => {
    setState({ data: null, loading: true, error: null });
    try {
      const response = await asyncFunction();
      setState({ data: response, loading: false, error: null });
    } catch (error) {
      setState({
        data: null,
        loading: false,
        error: error as ApiError,
      });
    }
  }, [asyncFunction]);

  useEffect(() => {
    if (immediate) {
      execute();
    }
  }, [execute, immediate]);

  return { ...state, refetch: execute };
}

export function useModels() {
  return useAsync(() => apiClient.getModels(), true);
}

export function useModel(id: string) {
  return useAsync(() => apiClient.getModel(id), !!id);
}

export function useUsageStats() {
  return useAsync(() => apiClient.getUsageStats(), true);
}

export function useApiKeys() {
  return useAsync(() => apiClient.getApiKeys(), true);
}

export function useBillingInfo() {
  return useAsync(() => apiClient.getBillingInfo(), true);
}

export function useCompletion() {
  const [state, setState] = useState({
    data: null,
    loading: false,
    error: null as ApiError | null,
  });

  const submit = useCallback(async (prompt: string, model: string, maxTokens = 1000, temperature = 0.7) => {
    setState({ data: null, loading: true, error: null });
    try {
      const response = await apiClient.completion({
        model,
        prompt,
        max_tokens: maxTokens,
        temperature,
      });
      setState({ data: response, loading: false, error: null });
      return response;
    } catch (error) {
      const apiError = error as ApiError;
      setState({ data: null, loading: false, error: apiError });
      throw apiError;
    }
  }, []);

  return { ...state, submit };
}

export function useApiKeyManagement() {
  const { data: keys, loading, error, refetch } = useApiKeys();
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  const createKey = useCallback(
    async (name: string) => {
      setCreating(true);
      try {
        await apiClient.createApiKey(name);
        await refetch();
      } catch (error) {
        throw error;
      } finally {
        setCreating(false);
      }
    },
    [refetch]
  );

  const deleteKey = useCallback(
    async (id: string) => {
      setDeleting(id);
      try {
        await apiClient.deleteApiKey(id);
        await refetch();
      } catch (error) {
        throw error;
      } finally {
        setDeleting(null);
      }
    },
    [refetch]
  );

  return {
    keys: keys || [],
    loading,
    error,
    creating,
    deleting,
    createKey,
    deleteKey,
    refetch,
  };
}
