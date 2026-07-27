# aicloud

White-label AI inference platform for aimodels.cloud

## Tech Stack

- **Frontend:** Next.js 15 + React 19 + TypeScript + Tailwind CSS
- **Backend:** Python FastAPI + SQLAlchemy + PostgreSQL
- **Inference:** LLM APIs (OpenAI, Anthropic, open-source models)
- **Deployment:** Vercel (frontend) + Docker (backend)
- **Analytics:** PostHog
- **Database:** PostgreSQL

## Architecture

```
aicloud/
├── frontend/           # Next.js app (dashboard, API playground)
├── api/                # FastAPI backend (inference, auth, analytics)
├── infra/              # Terraform/infrastructure-as-code
├── docs/               # API documentation
└── scripts/            # Deployment utilities
```

## Features (MVP)

- [ ] Dashboard with model browser
- [ ] API key management
- [ ] Request/response playground
- [ ] Usage analytics & billing
- [ ] Multiple model provider support
- [ ] Rate limiting & quota management
- [ ] White-label customization
- [ ] Developer documentation

## Local Development

```bash
# Frontend
npm install && npm run dev

# Backend
poetry install && poetry run uvicorn api.main:app --reload
```

## Deployment

Frontend: `git push origin main` → Vercel auto-deploys
Backend: Docker container + systemd service
