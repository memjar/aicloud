# GitHub Actions — CI/CD Pipeline

Automated testing, linting, and deployment to Vercel.

## Workflows

### 1. **deploy.yml** — Production Deployment

**Triggers:** Push to `main` branch

**What it does:**
1. Checks out code
2. Installs dependencies
3. Runs linter
4. Builds Next.js
5. Deploys to Vercel (production) OR creates preview
6. Comments on PRs with deployment URL

**Environment:** Production (main), Preview (PRs)

**Secrets Required:**
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`
- `NEXT_PUBLIC_ANALYTICS_KEY` (optional)

### 2. **lint-and-test.yml** — Code Quality Checks

**Triggers:** Push to `main`/`develop`, PRs

**What it does:**
1. ESLint check
2. TypeScript type checking
3. npm audit (security)
4. Build verification

**Environment:** Any branch

**No secrets required** (optional)

## Setup Checklist

- [ ] Create Vercel token
- [ ] Add `VERCEL_TOKEN` to GitHub Secrets
- [ ] Add `VERCEL_ORG_ID` to GitHub Secrets
- [ ] Add `VERCEL_PROJECT_ID` to GitHub Secrets
- [ ] Create Vercel project "aicloud"
- [ ] Configure domains in Vercel
- [ ] Update DNS records in Namecheap
- [ ] Push to `main` to trigger deployment
- [ ] Verify at https://aimodels.cloud

**Detailed setup:** See [SETUP_SECRETS.md](./SETUP_SECRETS.md)

## Workflow Status

View live status: https://github.com/memjar/aicloud/actions

## Quick Start

```bash
# Make a change
git add .
git commit -m "Update feature"

# Push to main
git push origin main

# GitHub Actions automatically:
# 1. Runs linting & tests
# 2. Builds Next.js
# 3. Deploys to Vercel
# 4. Updates aimodels.cloud

# Monitor at: https://github.com/memjar/aicloud/actions
```

## Branch Strategy

| Branch | Deploy To | Preview |
|--------|-----------|---------|
| `main` | Production (aimodels.cloud) | ✓ (with URL in PR) |
| `develop` | Vercel preview only | ✓ (auto URL) |
| feature/* | Skip deployment | ✓ (on PR to develop) |

## Environment Variables

### For Vercel Deployment

Set in **Vercel Project Settings → Environment Variables:**

```env
# Frontend
NEXT_PUBLIC_API_URL=https://api.aimodels.cloud
NEXT_PUBLIC_ANALYTICS_KEY=phc_xxxxx
NODE_ENV=production

# Secrets (not exposed to frontend)
DATABASE_URL=postgresql://...
STRIPE_API_KEY=sk_live_xxx
```

### For GitHub Workflow

Set in **GitHub Settings → Secrets → Actions:**

```env
VERCEL_TOKEN=xxxxx
VERCEL_ORG_ID=team_xxxxx
VERCEL_PROJECT_ID=prj_xxxxx
NEXT_PUBLIC_ANALYTICS_KEY=phc_xxxxx  # Optional
```

## Deployment Flow

```
Developer push → GitHub Actions
    ↓
Lint & Build Check
    ↓
Deploy to Vercel
    ├── main branch → Production (aimodels.cloud)
    └── Pull request → Preview URL
    ↓
Comment posted on PR (if applicable)
    ↓
Monitor at vercel.com/dashboard
```

## Monitoring

### Real-time Dashboard

- **GitHub Actions:** https://github.com/memjar/aicloud/actions
- **Vercel Deployments:** https://vercel.com/dashboard/aicloud/deployments

### Logs

```bash
# View in GitHub
# Actions → Latest run → Click deploy job

# View in Vercel
# Deployments → Select deployment → View logs
```

### Notifications

Configure alerts:
1. GitHub Settings → Notifications → Custom routing
2. Enable "Failed workflow run" notification
3. Vercel Settings → Notifications (email on deployment failure)

## Troubleshooting

**Deployment fails:**
1. Check GitHub Actions logs (red ✗)
2. Check Vercel deployment logs
3. Common issues:
   - Missing secrets → Update VERCEL_TOKEN
   - Build error → Check next.config.js
   - Environment vars → Verify in Vercel dashboard

**Preview URL not generated:**
- Only works on PRs with `github.event_name == 'pull_request'`
- Must have secrets configured
- Check `.github/workflows/deploy.yml` comments section

**DNS not resolving:**
- Wait 24-48 hours after updating Namecheap
- Run `dig aimodels.cloud @8.8.8.8`
- Verify DNS records in Namecheap match Vercel recommendation

See [SETUP_SECRETS.md](./SETUP_SECRETS.md) for detailed troubleshooting.

## Cost & Limits

| Service | Free Tier | Cost | Notes |
|---------|-----------|------|-------|
| **Vercel** | 100GB bandwidth/mo | $20/mo pro | Included: auto-SSL, CDN, analytics |
| **GitHub Actions** | 2,000 min/month | Free for public repos | Deployment workflow ≈ 2-3 min/run |

## Security

- ✅ Secrets encrypted in GitHub
- ✅ No secrets in code
- ✅ Environment-specific configs
- ✅ Automatic rollback available
- ✅ Preview deployments isolated from production

## Next Steps

1. **Complete setup:** Follow [SETUP_SECRETS.md](./SETUP_SECRETS.md)
2. **Push to trigger:** `git push origin main`
3. **Monitor:** https://github.com/memjar/aicloud/actions
4. **Verify deployment:** https://aimodels.cloud
5. **Add monitoring:** PostHog + Vercel Analytics

## Support

- GitHub Actions docs: https://docs.github.com/en/actions
- Vercel action: https://github.com/vercel/action
- Vercel docs: https://vercel.com/docs
