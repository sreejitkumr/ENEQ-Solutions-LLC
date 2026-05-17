# ENEQ Quotation Generator - Deployment Guide

Complete step-by-step instructions for deploying the application to production.

---

## 🚀 Quick Comparison

| Platform | Cost | Ease | Performance | Data Persistence |
|----------|------|------|-------------|------------------|
| **Streamlit Cloud** | Free | ⭐⭐⭐⭐⭐ | Good | SQLite/Files |
| **Heroku** | ~$7/month | ⭐⭐⭐⭐ | Good | Ephemeral |
| **Railway** | Pay-as-you-go | ⭐⭐⭐⭐ | Excellent | With storage |
| **Render** | Free tier | ⭐⭐⭐⭐ | Good | Ephemeral |
| **AWS/GCP/Azure** | Variable | ⭐⭐ | Excellent | Yes |

---

## Option 1: Streamlit Cloud (Recommended - Easiest)

### Prerequisites
- GitHub account with your code pushed
- Streamlit account (free)

### Step-by-Step Deployment

1. **Prepare your repository:**
   ```bash
   cd /Users/sreejitkumar/Downloads/eneq_quote_app-3
   git add .
   git commit -m "Prepare for production deployment"
   git push origin main
   ```

2. **Create Streamlit Secrets:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Select your GitHub repository
   - Choose branch and file (`app.py`)

3. **Configure Secrets:**
   - After deployment, go to app settings (hamburger menu → Settings)
   - Click "Secrets" tab
   - Paste your `.streamlit/secrets.toml` content:
     ```toml
     [smtp]
     password = "your-actual-smtp-password"
     ```

4. **Update default passwords:**
   - Log in with default credentials
   - Go to "Users" tab
   - Change all default passwords immediately

5. **Test the deployment:**
   - Test quotation generation
   - Test email functionality
   - Verify PDF download works

### Important Notes
- **Public Repository**: If using free tier, your repo must be public
- **File Persistence**: Data files in `data/` directory persist between deployments
- **Auto-Deployment**: Updates automatically when you push to GitHub

---

## Option 2: Heroku (Reliable Hosting)

### Prerequisites
- Heroku account (free tier available)
- Heroku CLI installed
- GitHub repository

### Step-by-Step Deployment

1. **Install Heroku CLI:**
   ```bash
   brew tap heroku/brew && brew install heroku
   heroku login
   ```

2. **Create Procfile:**
   ```bash
   cat > Procfile << 'EOF'
   web: streamlit run app.py --server.port $PORT --server.headless true --client.toolbarPosition=bottom
   EOF
   ```

3. **Create Heroku app:**
   ```bash
   heroku create your-app-name
   ```

4. **Set environment variables:**
   ```bash
   heroku config:set SMTP_PASSWORD="your-actual-smtp-password"
   ```

5. **Deploy:**
   ```bash
   git push heroku main
   ```

6. **View logs:**
   ```bash
   heroku logs --tail
   ```

### Important Notes
- **Data Storage**: Heroku filesystem is ephemeral. Use persistent storage for `data/` directory:
  - Option A: Use AWS S3 (more complex)
  - Option B: Use Heroku Postgres (requires paid plan)
  - Option C: Accept data loss on dyno restart

- **To persist data with GitHub:**
  ```bash
  heroku config:set USE_GITHUB_STORAGE=true
  heroku config:set GITHUB_TOKEN="your-github-token"
  ```

---

## Option 3: Railway (Modern & Easy)

### Prerequisites
- Railway account
- GitHub repository

### Step-by-Step Deployment

1. **Push code to GitHub:**
   ```bash
   git add .
   git commit -m "Ready for Railway deployment"
   git push origin main
   ```

2. **Deploy on Railway:**
   - Go to [railway.app](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Configure Environment:**
   - In Railway project, go to "Variables"
   - Add:
     ```
     SMTP_PASSWORD=your-actual-smtp-password
     ```

4. **Generate Domain:**
   - Railway auto-generates a public domain
   - Your app is live!

### Data Persistence
- Add Railway Postgres (paid) or SQLite volume (paid)
- For free tier, data persists on container but lost on redeploy

---

## Option 4: Render (Simple Free Tier)

### Prerequisites
- Render account
- GitHub repository

### Step-by-Step Deployment

1. **Create New Web Service:**
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect GitHub repository

2. **Configure Build Settings:**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run app.py --server.port 10000 --server.headless true`

3. **Add Environment Variables:**
   - Name: `SMTP_PASSWORD`
   - Value: `your-actual-smtp-password`

4. **Deploy:**
   - Click "Create Web Service"
   - Render automatically deploys

### Important Notes
- Free tier spins down after 15 minutes of inactivity
- Data persists during the session but lost when spun down
- Upgrade to paid for persistent data

---

## Option 5: AWS (Scalable Production)

### Prerequisites
- AWS account
- AWS CLI installed
- Docker (for containerization)

### Quick Setup with Elastic Beanstalk

1. **Create Dockerfile:**
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   EXPOSE 8501
   CMD streamlit run app.py --server.port 8501 --server.headless true
   ```

2. **Deploy with Elastic Beanstalk:**
   ```bash
   eb init -p docker eneq-quotation-app
   eb create eneq-production
   eb setenv SMTP_PASSWORD="your-password"
   eb deploy
   ```

3. **Configure S3 for data persistence:**
   - Create S3 bucket for `data/` directory
   - Update app code to sync with S3
   - Set up backup strategy

---

## Post-Deployment Checklist

- [ ] **Change default passwords** (Admin, Sales, Viewer)
- [ ] **Configure SMTP settings:**
  - SMTP Host (e.g., smtp.gmail.com)
  - SMTP Port (e.g., 587)
  - SMTP Username
  - SMTP Password (via environment variable/secrets)
- [ ] **Test email functionality** - Send a test quote
- [ ] **Enable HTTPS** (automatic on most platforms)
- [ ] **Set up backups** for `data/` directory
- [ ] **Configure custom domain** (if applicable)
- [ ] **Set up monitoring** and alerts
- [ ] **Test all user roles** (Admin, Sales, Viewer)
- [ ] **Document access credentials** securely

---

## Environment Variables Summary

| Variable | Required | Example | Where to Set |
|----------|----------|---------|--------------|
| `SMTP_PASSWORD` | Yes (if email enabled) | `App123!Password` | Secrets/Env Vars |
| `SMTP_HOST` | No (set in UI) | `smtp.gmail.com` | Admin Settings |
| `SMTP_USERNAME` | No (set in UI) | `noreply@company.com` | Admin Settings |

---

## Troubleshooting

### App Won't Start
```bash
# Check logs
heroku logs --tail              # Heroku
railway logs                     # Railway
render logs                      # Render
streamlit run app.py --logger.level=debug  # Local
```

### Email Not Working
- Verify SMTP credentials in Admin Settings
- Check SMTP password is set via environment variable
- Verify SMTP port is correct (usually 587 for TLS, 25 for unencrypted)
- Check that app password (not regular password) is used for Gmail/Office365

### Data Files Not Persisting
- Use platform-specific storage (see each option above)
- Or implement cloud storage integration (S3, GCS, Azure Blob)

### Performance Issues
- Upgrade to paid tier for more resources
- Optimize database queries
- Cache expensive operations

---

## Monitoring & Maintenance

### Regular Tasks
- **Weekly**: Check application logs for errors
- **Monthly**: Backup `data/` directory
- **Monthly**: Review user access and permissions
- **Quarterly**: Update Python dependencies
- **Quarterly**: Review and rotate SMTP credentials

### Setting Up Backups

**For Cloud Platforms:**
```bash
# Download data directory periodically
curl https://your-app.com/data/ -o backup-$(date +%Y%m%d).zip
```

**For Local VPS:**
```bash
# Add to crontab for daily backup
0 2 * * * tar -czf /backups/eneq-data-$(date +\%Y\%m\%d).tar.gz /app/data/
```

---

## Security Best Practices

1. **Use HTTPS everywhere** ✅ (Automatic on cloud platforms)
2. **Keep dependencies updated:**
   ```bash
   pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt --upgrade
   ```
3. **Rotate passwords quarterly** ✅
4. **Never commit secrets to git** ✅
5. **Use strong, unique passwords** ✅
6. **Enable 2FA on deployment platform** ✅
7. **Monitor access logs** ✅

---

## Performance Tips

- Use Streamlit Cloud for quick deployments (easiest)
- Use Railway/Render for balanced simplicity and performance
- Use Heroku for reliability with paid plans
- Use AWS for enterprise-scale deployments

---

## Support & Help

- **Streamlit Documentation**: https://docs.streamlit.io/deploy
- **Heroku Documentation**: https://devcenter.heroku.com/
- **Railway Documentation**: https://docs.railway.app/
- **Render Documentation**: https://render.com/docs

---

Last Updated: May 5, 2026
