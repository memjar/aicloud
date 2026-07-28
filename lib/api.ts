import axios, { AxiosInstance, AxiosError } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.aimodels.cloud';
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000;

interface ApiError {
  message: string;
  code?: string;
  status?: number;
}

interface CompletionRequest {
  model: string;
  prompt: string;
  max_tokens?: number;
  temperature?: number;
  top_p?: number;
}

interface CompletionResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: Array<{
    text: string;
    index: number;
    logprobs?: null;
    finish_reason: string;
  }>;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

interface Model {
  id: string;
  name: string;
  provider: string;
  type: string;
  costPer1k: string;
  latency: string;
  status: 'Available' | 'Running' | 'Unavailable';
  description?: string;
}

interface UsageStats {
  apiCalls30d: number;
  activeModels: number;
  avgLatency: number;
  cost30d: number;
  trend: {
    apiCalls: string;
    latency: string;
    cost: string;
  };
}

interface ApiKey {
  id: string;
  name: string;
  key: string;
  createdAt: string;
  lastUsed?: string;
  isActive: boolean;
}

interface BillingInfo {
  currentUsage: number;
  costThisMonth: number;
  totalTokens: number;
  planType: string;
  nextBillingDate: string;
}

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    this.client.interceptors.request.use((config) => {
      const apiKey = this.getApiKey();
      if (apiKey) {
        config.headers.Authorization = `Bearer ${apiKey}`;
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error) => this.handleError(error)
    );
  }

  private getApiKey(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('apiKey');
    }
    return null;
  }

  private async handleError(error: AxiosError): Promise<never> {
    const apiError: ApiError = {
      message: error.message,
      status: error.response?.status,
    };

    if (error.response?.data) {
      const data = error.response.data as Record<string, unknown>;
      apiError.message = (data.error as string) || apiError.message;
      apiError.code = data.code as string;
    }

    throw apiError;
  }

  private async retryRequest<T>(
    fn: () => Promise<T>,
    retries: number = MAX_RETRIES
  ): Promise<T> {
    try {
      return await fn();
    } catch (error) {
      if (retries > 0 && this.shouldRetry(error)) {
        await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY));
        return this.retryRequest(fn, retries - 1);
      }
      throw error;
    }
  }

  private shouldRetry(error: unknown): boolean {
    if (error instanceof AxiosError) {
      return !error.response || error.response.status >= 500;
    }
    return false;
  }

  async completion(request: CompletionRequest): Promise<CompletionResponse> {
    return this.retryRequest(() =>
      this.client
        .post<CompletionResponse>('/v1/completions', request)
        .then((res) => res.data)
    );
  }

  async getModels(): Promise<Model[]> {
    return this.retryRequest(() =>
      this.client
        .get<Model[]>('/v1/models')
        .then((res) => res.data)
    );
  }

  async getModel(id: string): Promise<Model> {
    return this.retryRequest(() =>
      this.client
        .get<Model>(`/v1/models/${id}`)
        .then((res) => res.data)
    );
  }

  async getUsageStats(): Promise<UsageStats> {
    return this.retryRequest(() =>
      this.client
        .get<UsageStats>('/v1/usage')
        .then((res) => res.data)
    );
  }

  async getApiKeys(): Promise<ApiKey[]> {
    return this.retryRequest(() =>
      this.client
        .get<ApiKey[]>('/v1/api-keys')
        .then((res) => res.data)
    );
  }

  async createApiKey(name: string): Promise<ApiKey> {
    return this.retryRequest(() =>
      this.client
        .post<ApiKey>('/v1/api-keys', { name })
        .then((res) => res.data)
    );
  }

  async deleteApiKey(id: string): Promise<void> {
    return this.retryRequest(() =>
      this.client.delete(`/v1/api-keys/${id}`).then(() => undefined)
    );
  }

  async getBillingInfo(): Promise<BillingInfo> {
    return this.retryRequest(() =>
      this.client
        .get<BillingInfo>('/v1/billing')
        .then((res) => res.data)
    );
  }

  setApiKey(key: string) {
    if (typeof window !== 'undefined') {
      localStorage.setItem('apiKey', key);
    }
  }

  clearApiKey() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('apiKey');
    }
  }
}

export const apiClient = new ApiClient();
export type { ApiError, CompletionRequest, CompletionResponse, Model, UsageStats, ApiKey, BillingInfo };
