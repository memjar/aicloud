# aimodel.cloud Architecture

White-label inference platform matching Baseten/Together.ai tech stack & feature parity.

## System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
├─────────────────────────────────────────────────────────────────┤
│ Next.js Dashboard (TypeScript + React 19 + Tailwind)            │
│ - Public landing page (aimodel.cloud)                           │
│ - Authenticated dashboard (models, usage, API keys)             │
│ - API playground (test endpoints)                               │
│ - Admin console (model management, billing)                     │
│ Hosted on: Vercel (auto-scaling, CDN, analytics)                │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                         API GATEWAY                             │
├─────────────────────────────────────────────────────────────────┤
│ FastAPI Server (Python 3.11+)                                   │
│ - Request validation & rate limiting                            │
│ - Auth (API keys, OAuth, webhooks)                              │
│ - Request routing & load balancing                              │
│ - Billing & quota enforcement                                   │
│ - Logging & analytics                                           │
│ Hosted on: Docker + ECS/K8s + Auto-scaling                      │
└─────────────────────────────────────────────────────────────────┘
                     ↙              ↘
        ┌────────────────────┐  ┌──────────────────┐
        │ MODEL PROVIDERS    │  │ DATA LAYER       │
        ├────────────────────┤  ├──────────────────┤
        │ • OpenAI API       │  │ PostgreSQL       │
        │ • Anthropic        │  │ (accounts, keys) │
        │ • Together.ai      │  │                  │
        │ • Local LLMs       │  │ Redis            │
        │ • Custom Models    │  │ (cache, session) │
        │                    │  │                  │
        │ Inference Queue    │  │ S3/Blob Storage  │
        │ (Celery/Bull)      │  │ (model weights)  │
        └────────────────────┘  └──────────────────┘
```

## Tech Stack (Parity with Competitors)

### Frontend
| Component | Technology | Reasoning |
|-----------|-----------|-----------|
| Framework | Next.js 15 | Same as Baseten, optimal for dashboards |
| UI Library | React 19 | Industry standard, TypeScript support |
| Styling | Tailwind CSS | Fast development, consistent design |
| Language | TypeScript | Type safety, DX, production-ready |
| Deploy | Vercel | Same as Baseten, auto-scaling, CDN, analytics |
| Analytics | PostHog | Same as Baseten, open-source alternative to Mixpanel |
| State | Zustand | Lightweight, no boilerplate |
| HTTP | Axios + TanStack Query | Efficient data fetching, caching |

### Backend
| Component | Technology | Reasoning |
|-----------|-----------|-----------|
| Framework | FastAPI | Python, fast, async, auto-docs (Swagger/OpenAPI) |
| Language | Python 3.11+ | ML ecosystem, inference libraries, async/await |
| Server | Uvicorn + Gunicorn | Production-ready ASGI server |
| Database | PostgreSQL | ACID, JSON support, scalability |
| ORM | SQLAlchemy | Type-safe, flexible, async support |
| Cache | Redis | Session management, rate limit tracking, caching |
| Queue | Celery + Redis | Async task processing (inference, webhooks) |
| Auth | JWT + OAuth2 | Standard, stateless, secure |
| Docs | FastAPI OpenAPI | Auto-generated, interactive |

### Infrastructure
| Component | Technology | Reasoning |
|-----------|-----------|-----------|
| Containerization | Docker | Reproducible builds, model versioning |
| Orchestration | Kubernetes (EKS) | Auto-scaling, load balancing, health checks |
| Inference Servers | VLLM + Ray | Batch processing, distributed inference |
| Model Registry | MLflow | Version control for models, reproducibility |
| Monitoring | Prometheus + Grafana | Observability, alerting |
| Logging | ELK Stack | Centralized logs, debugging |
| Tracing | Jaeger | Distributed tracing, latency analysis |
| Load Balancer | NGINX | Request routing, SSL termination |

### Data & ML
| Component | Technology | Reasoning |
|-----------|-----------|-----------|
| Model Serving | vLLM / TorchServe | Optimized inference, batching, quantization |
| Embeddings | sentence-transformers | Local embeddings, self-hosted |
| Vector DB | Pgvector (PostgreSQL) | Keep data in one place, ACID transactions |
| Feature Store | Feast | Feature management, versioning |
| Training | PyTorch / Hugging Face | Standard, ecosystem-rich |

## API Design

### Core Endpoints (REST + Streaming)
```
POST /v1/completions
POST /v1/chat/completions
POST /v1/embeddings
GET  /v1/models
POST /v1/models/{id}/infer
GET  /v1/usage
POST /v1/webhooks
```

### Authentication
```
Authorization: Bearer sk-xxx (API key)
X-Model-Override: model-id (per-request override)
X-Webhook-Secret: sig (webhook verification)
```

## Database Schema

### Core Tables
```sql
-- Accounts & Auth
accounts (id, email, org_name, stripe_id, created_at)
api_keys (id, account_id, key_hash, name, rate_limit, created_at)
oauth_tokens (id, account_id, provider, access_token, expires_at)

-- Models & Deployment
models (id, name, provider, version, config, status)
model_endpoints (id, model_id, url, status, latency_p99)
model_weights (id, model_id, s3_path, size_mb, format)

-- Requests & Billing
requests (id, account_id, model_id, tokens_in, tokens_out, cost, latency_ms, timestamp)
webhooks (id, account_id, event_type, url, retry_count, last_fired)
billing_cycles (account_id, period_start, period_end, total_cost, status)

-- Analytics
metrics (timestamp, account_id, model_id, requests_count, tokens_count, errors_count, p99_latency)
```

## Data Flow

### Inference Request
```
1. Client → API Gateway (auth + rate limit check)
2. Validate request, extract model choice, parameters
3. Route to model endpoint (load balancer selects instance)
4. Inference server processes (batching, quantization)
5. Response → cache (Redis) + log to database
6. Webhook fired (if subscribed)
7. Metrics updated (Prometheus)
8. Response returned to client
```

### Deployment
```
1. Model uploaded via dashboard
2. S3 storage + database record
3. Container built with model weights
4. Kubernetes deployment (rolling update)
5. Health checks & auto-restart
6. Metrics collected & exposed
7. Auto-scaling based on latency/queue
```

## Security

- **API Keys**: Hashed in DB, rotation policy
- **SSL/TLS**: All traffic encrypted (Vercel + NGINX)
- **CORS**: Whitelist per API key
- **Rate Limiting**: Per-key, per-IP, per-endpoint
- **Input Validation**: Pydantic models, sanitization
- **RBAC**: Account owner, team members, API-only access
- **Audit Logs**: All actions logged with user ID + timestamp
- **Data Isolation**: Account-scoped queries, tenant separation
- **Secrets Management**: AWS Secrets Manager, rotate regularly

## Scaling Strategy

### Horizontal
- Stateless API servers (scale up/down by demand)
- Load balancer distributes across instances
- Database read replicas for analytics queries

### Vertical
- Inference GPU nodes with auto-scaling groups
- Memory-optimized instances for large models
- SSD-backed storage for model weights

### Caching
- Redis for session state + rate limit counters
- CDN for static assets
- Model output caching (semantic deduplication)

## Monitoring & Observability

### Metrics (Prometheus)
- Request latency (p50, p95, p99)
- Requests per second
- Token usage (input/output)
- Error rate by model
- Cost per model

### Logs (ELK)
- Request logs (latency, tokens, cost)
- Error traces (stack traces, context)
- Model inference logs (performance, hardware utilization)
- API key activity (auth attempts, rate limits)

### Alerts
- P99 latency > 5s
- Error rate > 5%
- Pod restarts > 3 in 10min
- Disk usage > 80%
- Cost anomalies (30% spike vs baseline)

## Deployment Pipeline

```
1. Developer pushes to main/feature branch
2. CI/CD runs (tests, linting, security scan)
3. Frontend: Auto-deploy to Vercel
4. Backend: Docker build → ECR push → ECS deploy
5. Database migrations (flyway/alembic)
6. Smoke tests (health checks, sample inference)
7. Canary deployment (5% traffic → 100%)
8. Rollback on error (previous image)
```

## Cost Model

### Infrastructure
- Vercel: ~$20/mo (frontend)
- RDS PostgreSQL: ~$50/mo (db.t3.medium)
- Redis: ~$20/mo (managed service)
- ECS + EC2: ~$100-500/mo (depends on scale)
- S3 Storage: $0.023 per GB

### Pass-through (Model APIs)
- OpenAI: Varies by model
- Anthropic: Varies by model
- Local inference: Compute cost + margin

### White-label Pricing (Recommended)
- Developer: Free (10k requests/mo)
- Pro: $29/mo (1M requests included)
- Enterprise: Custom (dedicated compute + SLA)

## Feature Roadmap

### MVP (Week 1-2)
- [x] Landing page
- [x] Dashboard scaffold
- [x] API key management
- [x] Model browser
- [x] API playground
- [ ] Basic inference (OpenAI proxy)
- [ ] Request logging
- [ ] Rate limiting

### V1 (Week 3-4)
- [ ] Multi-model routing
- [ ] Webhooks
- [ ] Usage analytics
- [ ] Billing integration (Stripe)
- [ ] Custom models (upload + serve)
- [ ] Authentication (OAuth)
- [ ] Team management

### V2 (Month 2)
- [ ] Model fine-tuning
- [ ] Batch inference
- [ ] Cost optimization (quantization, caching)
- [ ] Advanced monitoring (distributed tracing)
- [ ] White-label customization
- [ ] Custom domain support
- [ ] SLA enforcement

## Competitive Advantages

1. **Parity with Baseten**: Same tech stack (Next.js, Vercel, Python backend)
2. **Better than Together.ai**: Custom domain, white-label branding
3. **Open-source friendly**: MLflow, vLLM, local model support
4. **Developer experience**: Built-in playground, auto-docs, webhooks
5. **Cost control**: Transparent pricing, usage alerts, quota management
6. **Privacy-first**: Option to self-host, data never leaves customer account
