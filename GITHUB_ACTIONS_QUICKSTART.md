# GitHub Actions Setup — Quick Start (5 minutes)

Your CI/CD pipeline is ready. Follow these steps to enable auto-deployment.

## 🚀 Step 1: Get Vercel Credentials (2 min)

### Create Vercel Token

Go to: https://vercel.com/account/tokens

Click **"Create Token"**
- Name: `github-actions-aicloud`
- Copy the token (you'll use it below)

### Get Vercel IDs

Go to: https://vercel.com/dashboard

Select **"aicloud"** project → Settings → General

Copy:
- **Project ID** (starts with `prj_`)
- **Org ID** (your team ID)

## 🔐 Step 2: Add GitHub Secrets (2 min)

Go to: https://github.com/memjar/aicloud/settings/secrets/actions

Click **"New repository secret"** for each:

| Secret | Value |
|--------|-------|
| `VERCEL_TOKEN` | Token from step 1 |
| `VERCEL_ORG_ID` | Team ID (team_xxx...) |
| `VERCEL_PROJECT_ID` | Project ID (prj_xxx...) |

**Example:**
```
Name: VERCEL_TOKEN
Value: xxxxxxxx_xxxxxx...xxx (paste from Vercel)
[Add secret]
```

Repeat for `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID`.

## ✅ Step 3: Configure Vercel Domains (1 min)

Go to: https://vercel.com/dashboard/aicloud → Settings → Domains

Add these domains:
- `aimodels.cloud`
- `www.aimodels.cloud`
- `aimodel.com.im` (optional)

Vercel will show you the DNS records to add.

## 🔗 Step 4: Update Namecheap DNS (1 min)

Go to: Namecheap → Your Domains → aimodels.cloud → Manage → Advanced DNS

Add these records:

| Type | Host | Value |
|------|------|-------|
| CNAME | @ | cname.vercel-dns.com. |
| CNAME | www | cname.vercel-dns.com. |

Same for `aimodel.com.im` if using that domain.

**Save changes.** (DNS may take 24-48 hours to propagate)

## 🚀 Step 5: Deploy! (1 min)

Make a small change and push to main:

```bash
# Clone the repo (if not already done)
git clone https://github.com/memjar/aicloud.git
cd aicloud

# Make a change (e.g., update README)
echo "# Live on aimodels.cloud!" >> README.md

# Commit and push
git add README.md
git commit -m "Deploy to production"
git push origin main
```

GitHub Actions will automatically:
1. ✓ Lint your code
2. ✓ Build Next.js
3. ✓ Deploy to Vercel
4. ✓ Update aimodels.cloud

## 📊 Monitor Deployment

**Watch live:**
- GitHub Actions: https://github.com/memjar/aicloud/actions
- Vercel Dashboard: https://vercel.com/dashboard/aicloud/deployments

**Expected in ~2 minutes:**
```
✓ Checkout code
✓ Setup Node.js
✓ Install dependencies
✓ Run linter
✓ Build Next.js
✓ Deploy to Vercel (Production)
✓ Notify on success
```

## ✨ Verify It Works

Wait 2-5 minutes, then check:

```bash
# Test DNS
dig aimodels.cloud @8.8.8.8

# Test HTTPS
curl -I https://aimodels.cloud

# Should return 200 OK with Vercel headers
```

Or just visit: **https://aimodels.cloud**

## 🎯 What's Automated Now

✅ **Production Deploy** → `git push origin main`  
✅ **Preview URLs** → Pull requests get live preview links  
✅ **Linting** → Code quality checks before deploy  
✅ **Build Verification** → Catches errors early  
✅ **Automatic Rollback** → One click in Vercel dashboard  

## 🆘 Troubleshooting

### "The specified token is not valid"
→ Generate a new Vercel token and update `VERCEL_TOKEN` secret

### Deployment still shows old version
→ Wait 24-48 hours for DNS propagation, then hard refresh (Cmd+Shift+R)

### Secrets not found error
→ Verify all 3 secrets exist at: https://github.com/memjar/aicloud/settings/secrets/actions

### Workflow not triggering
→ Make sure you pushed to `main` branch (not a feature branch)

**More help:** See `.github/SETUP_SECRETS.md` in the repo

## 📚 Next Steps

1. ✅ Complete steps 1-5 above
2. ✅ Verify deployment works
3. ⏳ Set environment variables (NEXT_PUBLIC_API_URL, etc.)
4. ⏳ Deploy backend API (to api.aimodels.cloud)
5. ⏳ Enable monitoring (PostHog, Vercel Analytics)
6. ⏳ Launch public beta

**Everything is set up. Just add the secrets and push!**

---

**Questions?** See:
- GitHub Actions setup: `.github/SETUP_SECRETS.md`
- Deployment guide: `DEPLOYMENT.md`
- Architecture: `ARCHITECTURE.md`
