# GitHub Actions Setup — Vercel Deployment

Complete guide to configure automated deployments to Vercel.

## Step 1: Get Vercel Credentials

### 1.1 Create/Get Vercel Token

```bash
# Option A: In Vercel Dashboard
# 1. Go to https://vercel.com/account/tokens
# 2. Click "Create Token"
# 3. Name it "github-actions-aicloud"
# 4. Copy the token (keep it secret!)

# Option B: Via Vercel CLI
vercel tokens create github-actions-aicloud
```

### 1.2 Get Vercel Organization & Project IDs

```bash
# From Vercel Dashboard:
# 1. Go to https://vercel.com/dashboard
# 2. Select "aicloud" project
# 3. Settings → General
# 4. Copy:
#    - Project ID (starts with "prj_")
#    - Org ID (in URL: /team/[ORG_ID]/)

# Or via CLI:
vercel projects list  # Shows Project ID
vercel teams list     # Shows Org ID
```

## Step 2: Add GitHub Secrets

Go to: **GitHub Repo Settings → Secrets and Variables → Actions**

Click "New repository secret" for each:

| Secret Name | Value | Source |
|-------------|-------|--------|
| `VERCEL_TOKEN` | `xxx...` | From Vercel tokens page |
| `VERCEL_ORG_ID` | `team_xxx...` | Vercel dashboard |
| `VERCEL_PROJECT_ID` | `prj_xxx...` | Vercel dashboard |
| `NEXT_PUBLIC_ANALYTICS_KEY` | `phc_xxx...` | PostHog (optional) |

### Visual Steps:

1. Go to: https://github.com/memjar/aicloud/settings/secrets/actions
2. Click **"New repository secret"**
3. Name: `VERCEL_TOKEN`
4. Value: (paste token from step 1.1)
5. Click **Add secret**
6. Repeat for remaining secrets

## Step 3: Test the Workflow

### Trigger Deployment

Push to main branch:
```bash
git push origin main
```

### Monitor Deployment

1. Go to: https://github.com/memjar/aicloud/actions
2. Watch the workflow run in real-time
3. Check status badge: [![Deploy to Vercel](../../.github/workflows/deploy.yml/badge.svg)](../../actions)

### Expected Flow

```
✓ Checkout code
✓ Setup Node.js
✓ Install dependencies
✓ Run linter
✓ Build Next.js
✓ Deploy to Vercel (Production)
✓ Notify on success
```

### Verify Deployment

```bash
# Check that aimodels.cloud is updated
curl -I https://aimodels.cloud
# Should return 200 OK with Vercel headers
```

## Step 4: Configure Domain Routing

**In Vercel Dashboard:**

1. Go to Project Settings → Domains
2. Add domains:
   - `aimodels.cloud`
   - `www.aimodels.cloud`
   - `aimodel.com.im` (optional)

**In Namecheap DNS (Advanced DNS):**

```
Type    Host    Value                      TTL
CNAME   @       cname.vercel-dns.com.      3600
CNAME   www     cname.vercel-dns.com.      3600
```

Wait 24-48 hours for DNS propagation.

## Step 5: Preview Deployments on PRs

GitHub Actions automatically:
- Creates **preview URLs** for pull requests
- Posts them as comments on PRs
- Keeps them live while PR is open

Example: PR → https://aicloud-pr-123.vercel.app

## Troubleshooting

### Workflow Fails with "Invalid Token"

```
Error: The specified token is not valid
```

**Solution:**
- Regenerate Vercel token (https://vercel.com/account/tokens)
- Update `VERCEL_TOKEN` secret with new value

### Deployment Stuck

**Check:**
- GitHub Actions status: https://github.com/memjar/aicloud/actions
- Vercel deployment logs: https://vercel.com/dashboard/aicloud
- Vercel status page: https://www.vercel-status.com

**Troubleshoot:**
```bash
# Run build locally to catch errors early
npm run build

# Test Vercel deployment locally
vercel --prod
```

### DNS Not Resolving

**Wait 24-48 hours** for DNS propagation, then:

```bash
# Check DNS records
dig aimodels.cloud @8.8.8.8
nslookup aimodels.cloud

# Expected output: Points to Vercel nameservers
```

## Next Steps

- ✅ GitHub Actions configured
- ✅ Vercel integration active
- ⏳ Push code to trigger first deployment
- ⏳ Configure environment variables
- ⏳ Set up monitoring (Vercel Analytics + PostHog)
- ⏳ Launch production

## Environment Variables

After secrets are configured, update these in **Vercel Project Settings → Environment Variables:**

```env
NEXT_PUBLIC_API_URL=https://api.aimodels.cloud
NEXT_PUBLIC_ANALYTICS_KEY=phc_xxxxx
NODE_ENV=production
```

## Rollback

If deployment breaks production:

```bash
# Option 1: Revert in GitHub
git revert <commit-hash>
git push origin main
# Workflow automatically redeploys

# Option 2: Rollback in Vercel Dashboard
# Vercel → Deployments → Select previous → "Rollback"
```

## Monitoring Deployments

### Real-time Logs

```bash
# View GitHub Actions logs
# https://github.com/memjar/aicloud/actions

# View Vercel deployment logs
# https://vercel.com/dashboard/aicloud/deployments
```

### Notifications

Configure in GitHub (optional):
- Settings → Notifications → Custom routing
- Get alerts on workflow success/failure

## Security Best Practices

✅ **Do:**
- Rotate `VERCEL_TOKEN` every 90 days
- Use branch protection rules (require PR reviews)
- Keep secrets out of git (use `.gitignore`)
- Monitor deployment logs for errors

❌ **Don't:**
- Commit secrets to git
- Share tokens in issues/PRs
- Use personal Vercel accounts
- Disable security checks

## Reference

- **Vercel Action:** https://github.com/vercel/action
- **GitHub Secrets:** https://docs.github.com/en/actions/security-guides/encrypted-secrets
- **Vercel Docs:** https://vercel.com/docs
- **Next.js Deployment:** https://nextjs.org/learn/basics/deploying-nextjs-app
