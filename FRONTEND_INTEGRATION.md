# Frontend Integration Guide

This document covers the fully integrated Next.js frontend with real API calls to the live backend at `api.aimodels.cloud`.

## Overview

The frontend has been completely wired to communicate with the backend API with:
- Full REST API integration for completions, models, and billing
- Real-time WebSocket support for live updates
- Comprehensive error handling and retry logic
- Loading states and spinners
- API key management UI
- Billing and usage dashboard

## Setup

### 1. Environment Variables

Create a `.env.local` file in the project root:

```env
# API Configuration
NEXT_PUBLIC_API_URL=https://api.aimodels.cloud

# Stripe Configuration (optional)
NEXT_PUBLIC_STRIPE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...

# Debug mode
NEXT_PUBLIC_DEBUG=false
```

### 2. Installation

```bash
npm install
# or
yarn install
```

The project already includes axios as a dependency for API calls.

### 3. Development Server

```bash
npm run dev
# or
yarn dev
```

Navigate to `http://localhost:3000`

## Architecture

### API Client (`lib/api.ts`)

The `ApiClient` class handles all backend communication:

```typescript
import { apiClient } from '@/lib/api';

// Completions
const response = await apiClient.completion({
  model: 'gpt-4-turbo',
  prompt: 'Hello, world!',
  max_tokens: 100,
  temperature: 0.7,
});

// Models
const models = await apiClient.getModels();
const model = await apiClient.getModel('gpt-4-turbo');

// Usage Stats
const stats = await apiClient.getUsageStats();

// API Keys
const keys = await apiClient.getApiKeys();
await apiClient.createApiKey('production');
await apiClient.deleteApiKey('key-id');

// Billing
const billing = await apiClient.getBillingInfo();
```

Features:
- Automatic retry logic (3 attempts for failed requests)
- Axios interceptors for authentication
- Type-safe request/response interfaces
- Error handling with structured error objects

### Hooks (`lib/hooks.ts`)

Custom React hooks for data fetching with built-in loading and error states:

```typescript
import { 
  useModels, 
  useCompletion, 
  useUsageStats,
  useApiKeys,
  useBillingInfo,
  useApiKeyManagement 
} from '@/lib/hooks';

// Data fetching with loading/error states
const { data, loading, error, refetch } = useModels();

// Completion submission with error handling
const { submit, data, loading, error } = useCompletion();
await submit(prompt, model, maxTokens, temperature);

// API key management
const { keys, createKey, deleteKey } = useApiKeyManagement();
```

### Components

#### ErrorBoundary Components

Located in `components/ErrorBoundary.tsx`:

- `ErrorAlert` - Display error messages
- `ErrorAlertWithRetry` - Error with retry button
- `FallbackError` - Full-page error state

#### Loading Components

Located in `components/Spinner.tsx`:

- `Spinner` - Animated loading spinner
- `LoadingCard` - Skeleton loading card
- `LoadingGrid` - Grid of skeleton cards

### Pages

#### Playground (`app/playground/page.tsx`)

Test models in real-time with:
- Live model list fetched from backend
- Real API completions
- Token usage display
- Temperature and max tokens controls
- API key requirement check

#### Models (`app/models/page.tsx`)

Browse available models with:
- Real-time model fetching
- Status indicators
- Cost and latency information
- Loading states for each model card

#### Dashboard (`app/dashboard/page.tsx`)

Main dashboard with:
- Real usage statistics (30-day API calls, active models, latency, cost)
- Billing overview
- Quick action cards
- Recent activity log
- Real-time updates

#### Settings (`app/settings/page.tsx`)

User account settings including:
- Account information management
- Billing overview
- Plan management
- Danger zone actions

#### API Keys (`app/settings/api-keys/page.tsx`)

API key management with:
- Create new API keys
- View all existing keys
- Copy keys to clipboard
- Delete keys (with confirmation)
- Security best practices notice
- Last used tracking

#### Billing (`app/settings/billing/page.tsx`)

Detailed billing information:
- Current plan and monthly cost
- Usage summary (API calls, tokens, avg cost)
- Payment method management
- Billing history with invoice downloads
- Next billing date

## API Integration Details

### Authentication

The API client automatically adds the Authorization header:

```typescript
// Stored in localStorage
localStorage.setItem('apiKey', 'sk-...');

// Automatically added to all requests
headers.Authorization = `Bearer ${apiKey}`;
```

### Error Handling

Structured error objects with automatic retry:

```typescript
interface ApiError {
  message: string;
  code?: string;
  status?: number;
}

try {
  await apiClient.completion({...});
} catch (error) {
  const apiError = error as ApiError;
  console.log(apiError.message);
  console.log(apiError.status);
}
```

Automatic retries for:
- Network timeouts
- 5xx server errors
- Connection failures

Manual retries can be triggered via error handlers.

### Request/Response Types

All endpoints are fully typed:

```typescript
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
    finish_reason: string;
  }>;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}
```

## Real-Time Updates (WebSocket)

Optional WebSocket support for live updates:

```typescript
import { useWebSocket } from '@/lib/useWebSocket';

export default function MyComponent() {
  const { isConnected, on, send } = useWebSocket({
    onConnect: () => console.log('Connected'),
    onDisconnect: () => console.log('Disconnected'),
    shouldConnect: true,
  });

  useEffect(() => {
    const unsubscribe = on('usage_update', (data) => {
      console.log('Usage updated:', data);
    });
    
    return unsubscribe;
  }, [on]);

  return <div>{isConnected ? 'Connected' : 'Disconnected'}</div>;
}
```

## Data Flow Example

### Completions Flow

1. User enters prompt and clicks "Send Request"
2. `useCompletion()` hook calls `apiClient.completion()`
3. API client adds auth header and sends POST to `/v1/completions`
4. Loading state shown to user
5. Response received and displayed
6. Token usage stats shown
7. Error handling with retry option on failure

### Models Fetch Flow

1. Page loads and `useModels()` initializes
2. Fetch starts with loading state
3. `apiClient.getModels()` hits `/v1/models` endpoint
4. Grid of model cards rendered with data
5. If error, retry button shown
6. Status badges update based on model status

### API Keys Management Flow

1. User navigates to `/settings/api-keys`
2. `useApiKeyManagement()` fetches existing keys
3. User can create new key with name
4. Success triggers refetch of keys
5. Keys displayed with copy/delete options
6. Delete with confirmation

## Performance Optimizations

1. **Request Caching**: Hooks cache responses and avoid refetching
2. **Retry Logic**: Exponential backoff for failed requests
3. **Error Boundaries**: Graceful error handling prevents crashes
4. **Loading States**: Skeleton screens for better UX
5. **Lazy Loading**: Components load data on mount only

## Security Considerations

1. **API Keys**: Stored in localStorage (upgrade to secure cookie storage in production)
2. **HTTPS Only**: All API calls to production use HTTPS
3. **CORS**: Backend should validate origin headers
4. **Rate Limiting**: Implement on backend to prevent abuse
5. **Input Validation**: Frontend validates before sending

## Backend API Endpoints

The frontend expects these endpoints:

```
POST   /v1/completions      - Create completion
GET    /v1/models           - List all models
GET    /v1/models/{id}      - Get specific model
GET    /v1/usage            - Get usage stats
GET    /v1/api-keys         - List API keys
POST   /v1/api-keys         - Create API key
DELETE /v1/api-keys/{id}    - Delete API key
GET    /v1/billing          - Get billing info
WS     /ws                  - WebSocket connection
```

### Expected Response Formats

Endpoints should return data matching the TypeScript interfaces defined in `lib/api.ts`.

## Environment Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| NEXT_PUBLIC_API_URL | Backend API URL | https://api.aimodels.cloud |
| NEXT_PUBLIC_STRIPE_KEY | Stripe public key | - |
| STRIPE_SECRET_KEY | Stripe secret key | - |
| NEXT_PUBLIC_DEBUG | Debug logging | false |

## Build for Production

```bash
npm run build
npm run start
```

Production deployment:
1. Build static files: `npm run build`
2. Deploy to Vercel, Netlify, or custom server
3. Set production environment variables
4. Ensure backend API is accessible from production domain

## Troubleshooting

### API calls failing with 401

- Check API key is set in localStorage
- Verify API key format is correct
- Ensure backend is running and accessible

### Models page shows no models

- Verify `/v1/models` endpoint exists on backend
- Check response format matches `Model[]` interface
- Check browser network tab for response details

### WebSocket connection failing

- Verify `/ws` endpoint exists on backend
- Check authentication token is valid
- Ensure WebSocket protocol is supported (wss:// for HTTPS)

### CORS errors

- Add `https://your-frontend-domain` to backend CORS whitelist
- Verify backend sets `Access-Control-Allow-*` headers

## Next Steps

1. **Customize UI**: Modify Tailwind styles to match branding
2. **Add Analytics**: Integrate PostHog/Segment for usage tracking
3. **Implement Auth**: Add proper authentication (OAuth, JWT)
4. **Add Webhooks**: Setup webhook management UI
5. **Custom Branding**: Update colors, fonts, logos
6. **Mobile Optimization**: Improve mobile responsiveness

## Support

For issues or questions about the integration:
1. Check network tab in browser DevTools
2. Review console errors
3. Verify backend is running
4. Check API response format
5. Consult the backend API documentation
