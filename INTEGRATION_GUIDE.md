# Backend Integration Guide — Connecting to AI Model Providers

How to wire up aimodels.cloud to actually serve inference from OpenAI, Anthropic, Together.ai, and local models.

## Architecture Overview

```
User Request
    ↓
Frontend (Next.js) → Dashboard, Playground, Models
    ↓
API Gateway (FastAPI) ← Authentication, Rate Limiting, Billing
    ↓
Model Router ← Route to correct provider
    ↓
Provider Adapters
├── OpenAI Adapter
├── Anthropic Adapter
├── Together.ai Adapter
└── Local Model Server
    ↓
Response → Cache → Return to User
```

## Step 1: Environment Setup

Create `.env.production`:
```env
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Together.ai
TOGETHER_API_KEY=...

# Database
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# Stripe (for billing)
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_KEY=whsec_...
```

## Step 2: Create Provider Adapters

### OpenAI Adapter (`backend/src/adapters/openai.py`)

```python
import openai
from typing import Dict, Any

class OpenAIAdapter:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
    
    async def infer(
        self,
        model: str,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> Dict[str, Any]:
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        return {
            "id": response.id,
            "model": response.model,
            "content": response.choices[0].message.content,
            "tokens_in": response.usage.prompt_tokens,
            "tokens_out": response.usage.completion_tokens,
            "cost": self._calculate_cost(model, response.usage)
        }
    
    def _calculate_cost(self, model: str, usage) -> float:
        # OpenAI pricing (as of Jan 2026)
        pricing = {
            "gpt-4-turbo": {"input": 0.01 / 1000, "output": 0.03 / 1000},
            "gpt-4": {"input": 0.03 / 1000, "output": 0.06 / 1000},
            "gpt-3.5-turbo": {"input": 0.0005 / 1000, "output": 0.0015 / 1000},
        }
        
        if model not in pricing:
            return 0
        
        rate = pricing[model]
        cost = (usage.prompt_tokens * rate["input"]) + (usage.completion_tokens * rate["output"])
        return cost
```

### Anthropic Adapter (`backend/src/adapters/anthropic.py`)

```python
import anthropic
from typing import Dict, Any

class AnthropicAdapter:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
    
    async def infer(
        self,
        model: str,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> Dict[str, Any]:
        response = self.client.messages.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        return {
            "id": response.id,
            "model": response.model,
            "content": response.content[0].text,
            "tokens_in": response.usage.input_tokens,
            "tokens_out": response.usage.output_tokens,
            "cost": self._calculate_cost(model, response.usage)
        }
    
    def _calculate_cost(self, model: str, usage) -> float:
        # Anthropic pricing (as of Jan 2026)
        pricing = {
            "claude-3-opus-20250219": {"input": 0.015 / 1000, "output": 0.075 / 1000},
            "claude-3-sonnet-20250229": {"input": 0.003 / 1000, "output": 0.015 / 1000},
            "claude-3-haiku-20250307": {"input": 0.00080 / 1000, "output": 0.004 / 1000},
        }
        
        if model not in pricing:
            return 0
        
        rate = pricing[model]
        cost = (usage.input_tokens * rate["input"]) + (usage.output_tokens * rate["output"])
        return cost
```

### Together.ai Adapter (`backend/src/adapters/together.py`)

```python
import together
from typing import Dict, Any

class TogetherAdapter:
    def __init__(self, api_key: str):
        together.api_key = api_key
    
    async def infer(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> Dict[str, Any]:
        response = together.Complete.create(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        return {
            "id": response.get("id"),
            "model": model,
            "content": response["output"]["choices"][0]["text"],
            "tokens_in": 0,  # Together doesn't always return token counts
            "tokens_out": len(response["output"]["choices"][0]["text"].split()),
            "cost": self._calculate_cost(model, response)
        }
    
    def _calculate_cost(self, model: str, response) -> float:
        # Together.ai pricing (much cheaper for open source)
        pricing = {
            "meta-llama/Llama-2-70b": 0.0008 / 1000,
            "meta-llama/Llama-2-13b": 0.0003 / 1000,
            "mistralai/Mistral-7B": 0.0002 / 1000,
        }
        
        tokens = len(response["output"]["choices"][0]["text"].split())
        return tokens * pricing.get(model, 0)
```

## Step 3: Model Router (`backend/src/routes/infer.py`)

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional

router = APIRouter(prefix="/v1", tags=["inference"])

class Message(BaseModel):
    role: str
    content: str

class InferenceRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1024

@router.post("/completions")
async def completions(request: InferenceRequest):
    """Route to appropriate model provider"""
    
    model = request.model
    
    # Determine provider by model name
    if model.startswith("gpt"):
        provider = "openai"
    elif model.startswith("claude"):
        provider = "anthropic"
    elif model.startswith("meta-llama") or model.startswith("mistralai"):
        provider = "together"
    else:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model}")
    
    # Get adapter for provider
    adapter = get_adapter(provider)
    
    try:
        # Call provider's API
        result = await adapter.infer(
            model=model,
            messages=[{"role": m.role, "content": m.content} for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        
        # Log for billing
        await log_request(
            model=model,
            provider=provider,
            tokens_in=result["tokens_in"],
            tokens_out=result["tokens_out"],
            cost=result["cost"],
        )
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_adapter(provider: str):
    adapters = {
        "openai": OpenAIAdapter(os.getenv("OPENAI_API_KEY")),
        "anthropic": AnthropicAdapter(os.getenv("ANTHROPIC_API_KEY")),
        "together": TogetherAdapter(os.getenv("TOGETHER_API_KEY")),
    }
    return adapters[provider]
```

## Step 4: Billing Integration (`backend/src/billing.py`)

```python
import stripe
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

stripe.api_key = os.getenv("STRIPE_API_KEY")

async def log_request(
    model: str,
    provider: str,
    tokens_in: int,
    tokens_out: int,
    cost: float,
):
    """Log API request for billing"""
    
    db = Session(engine)
    
    request_log = RequestLog(
        model=model,
        provider=provider,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        cost=cost,
        timestamp=datetime.utcnow(),
    )
    
    db.add(request_log)
    db.commit()
    
    # Update user's current month billing
    user_billing = db.query(UserBilling).filter(
        UserBilling.user_id == current_user.id,
        UserBilling.month == datetime.utcnow().month
    ).first()
    
    if user_billing:
        user_billing.total_cost += cost
        user_billing.total_tokens += tokens_in + tokens_out
        db.commit()

async def charge_monthly():
    """Monthly billing charge"""
    
    db = Session(engine)
    billings = db.query(UserBilling).filter(
        UserBilling.charged == False
    ).all()
    
    for billing in billings:
        try:
            charge = stripe.Charge.create(
                amount=int(billing.total_cost * 100),  # Convert to cents
                currency="usd",
                customer=billing.user.stripe_customer_id,
                description=f"aimodels.cloud - {billing.month} charges",
            )
            
            billing.charged = True
            billing.invoice_id = charge.id
            db.commit()
        
        except stripe.error.CardError as e:
            # Handle failed payment
            notify_user(billing.user, f"Payment failed: {e.message}")
```

## Step 5: Deploy Backend

```bash
# Install dependencies
poetry install

# Run migrations
poetry run alembic upgrade head

# Start API server
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000

# Or deploy to AWS ECS
docker build -t aimodels-api backend/
docker tag aimodels-api:latest [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com/aimodels-api:latest
docker push [ACCOUNT_ID].dkr.ecr.us-east-1.amazonaws.com/aimodels-api:latest
aws ecs update-service --cluster aimodels-prod --service aimodels-api --force-new-deployment
```

## Step 6: Wire Frontend to Backend

Update playground to call actual API:

```typescript
// app/playground/page.tsx
async function handleSubmit(e: React.FormEvent) {
  e.preventDefault();
  setLoading(true);

  try {
    const res = await fetch('https://api.aimodels.cloud/v1/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model,
        messages: [{ role: 'user', content: prompt }],
        temperature,
        max_tokens,
      }),
    });

    const data = await res.json();
    setResponse(data.content);
  } catch (error) {
    setResponse(`Error: ${error}`);
  } finally {
    setLoading(false);
  }
}
```

## Cost Breakdown (per 1M tokens)

| Provider | Input Cost | Output Cost | Best For |
|----------|-----------|-------------|----------|
| OpenAI GPT-4 Turbo | $10 | $30 | Complex reasoning |
| Anthropic Claude 3 Opus | $15 | $75 | Nuanced tasks |
| Anthropic Claude 3 Haiku | $0.80 | $4 | Fast, cheap |
| Together Llama-2 70B | $0.80 | $0.80 | Open source, fast |
| Mistral 7B | $0.20 | $0.20 | Ultra-cheap |

**Markup Strategy**: Charge 2-3x provider cost
- Llama-2: Provider cost $1.60 → Charge $4-5 → 250-300% margin
- GPT-4: Provider cost $40 → Charge $80-100 → 100-150% margin
- Claude 3 Opus: Provider cost $90 → Charge $180-200 → 100-122% margin

## Next Steps

1. ✅ Frontend deployed (aicloud-dusky.vercel.app)
2. ⏳ Backend API (add to api.aimodels.cloud)
3. ⏳ Wire adapters with API keys
4. ⏳ Connect to Stripe for billing
5. ⏳ Test end-to-end inference
6. ⏳ Launch to users

**Estimated time to production**: 1-2 weeks
