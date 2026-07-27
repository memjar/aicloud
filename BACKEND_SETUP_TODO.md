# Backend Setup TODO

Complete backend infrastructure setup for aimodels.cloud API.

## 📋 Task List

### Phase 1: Local Development Setup

- [ ] Create Python virtual environment
  ```bash
  cd backend
  python3.11 -m venv venv
  source venv/bin/activate
  poetry install
  ```

- [ ] Create `.env.local` with:
  ```env
  DATABASE_URL=sqlite:///./test.db  # For local testing
  REDIS_URL=redis://localhost:6379
  API_PORT=8000
  LOG_LEVEL=DEBUG
  STRIPE_API_KEY=sk_test_xxx
  ```

- [ ] Start local dev server
  ```bash
  cd backend
  poetry run uvicorn src.main:app --reload --port 8000
  ```

- [ ] Test health endpoint
  ```bash
  curl http://localhost:8000/health
  # Expected: {"status": "healthy", "service": "aicloud-api"}
  ```

### Phase 2: Database Setup

- [ ] Create PostgreSQL database
  ```bash
  createdb aimodels_dev
  createdb aimodels_prod
  ```

- [ ] Install pgvector extension
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```

- [ ] Run migrations
  ```bash
  poetry run alembic upgrade head
  ```

- [ ] Create tables:
  - `accounts` (users)
  - `api_keys` (authentication)
  - `models` (model registry)
  - `requests` (logging & billing)
  - `webhooks` (event subscriptions)

### Phase 3: Authentication & API Keys

- [ ] Implement JWT token generation
- [ ] Create API key hashing & storage
- [ ] Implement rate limiting (Redis-backed)
- [ ] Add OAuth2 integration (optional)

### Phase 4: Model Serving

- [ ] Install vLLM for inference
- [ ] Create model loader service
- [ ] Implement multi-model router
- [ ] Add model versioning support
- [ ] Cache model weights (S3/blob storage)

### Phase 5: Core API Endpoints

- [ ] `POST /v1/completions` — LLM inference
- [ ] `POST /v1/chat/completions` — Chat interface
- [ ] `POST /v1/embeddings` — Embedding generation
- [ ] `GET /v1/models` — List available models
- [ ] `GET /v1/usage` — Account usage stats
- [ ] `POST /v1/webhooks` — Event subscriptions

### Phase 6: Integrations

- [ ] OpenAI API proxy
- [ ] Anthropic API proxy
- [ ] Together.ai API proxy
- [ ] Local model serving (Ollama/vLLM)
- [ ] Stripe billing integration

### Phase 7: Monitoring & Logging

- [ ] Set up PostHog event tracking
- [ ] CloudWatch logs (AWS)
- [ ] Prometheus metrics
- [ ] Distributed tracing (Jaeger)
- [ ] Error reporting (Sentry)

### Phase 8: Deployment to AWS

- [ ] Create ECR repository
  ```bash
  aws ecr create-repository --repository-name aimodels-api
  ```

- [ ] Build & push Docker image
  ```bash
  docker build -t aimodels-api backend/
  docker tag aimodels-api:latest [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com/aimodels-api:latest
  docker push [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com/aimodels-api:latest
  ```

- [ ] Create ECS cluster
- [ ] Create task definition
- [ ] Set up load balancer (ALB)
- [ ] Configure auto-scaling
- [ ] Set up RDS PostgreSQL
- [ ] Set up ElastiCache Redis

### Phase 9: API Documentation

- [ ] Add OpenAPI/Swagger documentation
  - FastAPI auto-generates at `/docs`
- [ ] Create SDK examples (Python, JavaScript, cURL)
- [ ] Document authentication
- [ ] Create rate limiting docs
- [ ] Add error handling guide

### Phase 10: Testing

- [ ] Unit tests (pytest)
- [ ] Integration tests
- [ ] Load testing (locust)
- [ ] Security scanning (bandit)
- [ ] API contract testing

---

## 🔧 Current Backend Status

**Location:** `/backend`

**Structure:**
```
backend/
├── src/
│   ├── main.py              # FastAPI app entry
│   ├── models.py            # Database models
│   ├── schemas.py           # Request/response schemas
│   ├── routes/              # API endpoints
│   │   ├── infer.py        # Inference endpoints
│   │   ├── models.py       # Model management
│   │   ├── auth.py         # Authentication
│   │   └── webhooks.py     # Webhook handling
│   └── utils/              # Utilities
│       ├── cache.py        # Redis caching
│       ├── rate_limit.py   # Rate limiting
│       └── billing.py      # Stripe integration
├── tests/                  # Test suite
├── Dockerfile              # Container config
├── pyproject.toml          # Dependencies
├── alembic/                # Database migrations
└── .env.example            # Environment template
```

---

## 📚 Dependencies Already Defined

In `pyproject.toml`:
- FastAPI (async web framework)
- Uvicorn (ASGI server)
- SQLAlchemy (ORM)
- Pydantic (data validation)
- Python-dotenv (config management)
- psycopg2 (PostgreSQL driver)

---

## 🚀 Quick Start Commands

```bash
# Create venv
cd backend
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
poetry install

# Create local database
createdb aimodels_dev

# Run migrations
poetry run alembic upgrade head

# Start dev server
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# View API docs
# Open http://localhost:8000/docs
```

---

## 🔗 Integration Points

**Frontend → Backend:**
- Requests to `/api/*` proxied to `https://api.aimodels.cloud`
- Configured in `vercel.json` rewrites

**Backend → External APIs:**
- OpenAI (chat completions, embeddings)
- Anthropic (claude-3 family)
- Together.ai (open source models)
- Stripe (billing)

**Backend → Data:**
- PostgreSQL (primary datastore)
- Redis (cache, rate limiting)
- S3/Blob (model weights)

---

## 📊 Estimated Effort

| Phase | Tasks | Est. Time |
|-------|-------|-----------|
| Local Dev | 4 | 2 hours |
| Database | 4 | 2 hours |
| Auth | 3 | 3 hours |
| Model Serving | 5 | 8 hours |
| Core API | 6 | 12 hours |
| Integrations | 5 | 10 hours |
| Monitoring | 5 | 5 hours |
| Deployment | 6 | 6 hours |
| Docs | 5 | 4 hours |
| Testing | 5 | 8 hours |
| **Total** | **48** | **~60 hours** |

---

## 🎯 Priority Order

1. **Must Have (MVP):** Phases 1-5 (local dev + core API)
2. **Should Have:** Phases 6-7 (integrations + monitoring)
3. **Nice to Have:** Phases 8-10 (deployment + testing)

**Minimum viable backend:** Phases 1-5 only (~30 hours)

---

## 💾 Notes for Later

- Use async/await everywhere (FastAPI's strength)
- Implement database migrations from day one (alembic)
- Add logging early (helps debugging later)
- Use dependency injection for testing
- Keep API versioning in mind (`/v1/`, `/v2/`)
- Document as you go (OpenAPI is auto-generated)

---

## 📞 Reference Docs

- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- Alembic: https://alembic.sqlalchemy.org/
- Pydantic: https://docs.pydantic.dev/
- Poetry: https://python-poetry.org/docs/
- PostHog: https://posthog.com/docs
- AWS ECS: https://docs.aws.amazon.com/ecs/
