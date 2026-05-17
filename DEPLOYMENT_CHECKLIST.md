# ENEQ Quotation Generator - Pre-Deployment Checklist

Use this checklist to ensure your application is ready for production deployment.

## 🔐 Security Setup (CRITICAL)

- [ ] All default passwords changed:
  - [ ] Admin password changed
  - [ ] Sales password changed
  - [ ] Viewer password changed
- [ ] SMTP password is set via environment variable or Streamlit secrets
- [ ] `.streamlit/secrets.toml` created and populated
- [ ] `.streamlit/secrets.toml` is in `.gitignore` (never commit)
- [ ] `data/users.csv` is in `.gitignore`
- [ ] `data/settings.json` is in `.gitignore`
- [ ] All sensitive config removed from `data/settings.json`
- [ ] Code doesn't contain hardcoded passwords or API keys

## 📦 Deployment Files

- [ ] `Procfile` created (for Heroku)
- [ ] `Dockerfile` created (for Docker/Railway/GCP)
- [ ] `docker-compose.yml` created (for local testing)
- [ ] `.dockerignore` created
- [ ] `.streamlit/config.toml` created
- [ ] `DEPLOYMENT_GUIDE.md` reviewed
- [ ] `deploy.sh` script created and tested

## 🧪 Local Testing

- [ ] Application runs locally: `streamlit run app.py`
- [ ] All user roles work:
  - [ ] Admin role - can access all tabs
  - [ ] Sales role - can generate quotes
  - [ ] Viewer role - can only view history
- [ ] Quotation generation works
- [ ] PDF download works
- [ ] Email functionality tested (if configured)
- [ ] CSV file parsing works
- [ ] Bundle catalog upload tested
- [ ] Pricing catalog upload tested

## 📋 Code Quality

- [ ] Code committed to Git
- [ ] All files pushed to GitHub
- [ ] No Python syntax errors
- [ ] No missing dependencies
- [ ] `requirements.txt` is up to date
- [ ] No debug statements left in code
- [ ] Comments are clear and helpful

## ☁️ Deployment Platform Specific

### For Streamlit Cloud
- [ ] GitHub repository is public
- [ ] Repository is connected to Streamlit Cloud
- [ ] Secrets configured in Streamlit Cloud settings
- [ ] SMTP password added to secrets

### For Heroku
- [ ] Heroku account created
- [ ] Heroku CLI installed: `heroku --version`
- [ ] Logged in to Heroku: `heroku login`
- [ ] App created on Heroku
- [ ] Environment variables set: `heroku config`
- [ ] Dyno type selected (free or paid)

### For Railway
- [ ] Railway account created
- [ ] GitHub repository connected
- [ ] Project created on Railway
- [ ] Environment variables configured
- [ ] Custom domain (optional) configured

### For Docker
- [ ] Docker installed: `docker --version`
- [ ] Docker image builds successfully: `docker build -t eneq-app .`
- [ ] Container runs: `docker run -p 8501:8501 eneq-app`
- [ ] Data volumes mounted correctly

## 🔧 Infrastructure Setup

- [ ] Database backup strategy defined
- [ ] Data persistence solution chosen:
  - [ ] Cloud storage (S3, GCS, Azure Blob)
  - [ ] Platform storage (Railway Postgres, Heroku Postgres)
  - [ ] Accept data loss on redeploy
- [ ] Backup schedule configured
- [ ] Monitoring/alerting configured (if available)

## 📧 Email Configuration

- [ ] SMTP host verified to work
- [ ] SMTP port correct (usually 587 for TLS)
- [ ] SMTP username correct
- [ ] SMTP password secure (environment variable)
- [ ] Test email sent successfully
- [ ] Email template looks good
- [ ] Attachments working (PDF)

## 📊 Data Setup

- [ ] `data/bundle_catalog.csv` populated with products
- [ ] `data/bundle_components.csv` populated with components
- [ ] `data/pricing.csv` populated with prices
- [ ] Sample data cleaned up (remove test entries)
- [ ] Pricing is accurate
- [ ] VAT percentage correct
- [ ] Default margin percentage set appropriately

## 🌐 Domain & SSL

- [ ] Custom domain configured (if applicable)
- [ ] SSL certificate installed (auto on most platforms)
- [ ] HTTPS redirect enabled
- [ ] Domain DNS records verified

## 📚 Documentation

- [ ] `README.md` updated with deployment info
- [ ] `DEPLOYMENT_GUIDE.md` reviewed
- [ ] Admin documentation created
- [ ] User guide created
- [ ] Troubleshooting guide created
- [ ] Access credentials documented securely

## ✅ Final Checks

- [ ] Test complete user flow:
  1. [ ] Login with different roles
  2. [ ] Generate a quotation
  3. [ ] Download PDF
  4. [ ] Send via email
  5. [ ] View quotation history
- [ ] Performance acceptable
- [ ] No error messages in logs
- [ ] Mobile responsiveness tested
- [ ] Different browsers tested
- [ ] All links working
- [ ] Team trained on system

## 🚀 Go Live

- [ ] All items above checked ✅
- [ ] Stakeholders notified
- [ ] Deployment scheduled (if needed)
- [ ] Rollback plan in place
- [ ] Support team briefed
- [ ] Monitoring active
- [ ] Alert recipients configured

---

## Quick Deployment Command

```bash
# Choose your platform:

# Streamlit Cloud
git add . && git commit -m "Deploy to Streamlit Cloud" && git push

# Heroku
git add . && git commit -m "Deploy to Heroku" && git push heroku main

# Railway/Render
git add . && git commit -m "Deploy to Railway" && git push origin main

# Docker
docker build -t eneq-quotation-app .
docker run -p 8501:8501 -e SMTP_PASSWORD="your-password" eneq-quotation-app
```

---

**Deployment Status:** ☐ Not Started  ☐ In Progress  ☐ Completed ✅

**Deployed By:** _________________________  
**Date:** _________________________  
**Environment:** [ ] Dev  [ ] Staging  [ ] Production  

**Notes:**
```
[Add any deployment notes here]
```
