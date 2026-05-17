# 🚀 Quick Deployment Reference

Fast deployment instructions for the most common platforms.

---

## ⭐ Fastest (Streamlit Cloud) - 5 minutes

```bash
# 1. Ensure code is on GitHub
git add .
git commit -m "Ready for deployment"
git push origin main

# 2. Go to https://share.streamlit.io
# Click "New app" → Select your GitHub repo → app.py
# Wait for deployment (2-3 minutes)

# 3. Add secrets
# After deployed: Menu → Settings → Secrets
# Paste your .streamlit/secrets.toml content

# 4. Change default passwords
# Login and update all user passwords in Admin panel
```

---

## 🟣 Reliable (Heroku) - 10 minutes

```bash
# 1. Install Heroku CLI
brew tap heroku/brew && brew install heroku

# 2. Create and deploy
heroku login
heroku create your-app-name
heroku config:set SMTP_PASSWORD="your-password"
git push heroku main

# 3. Monitor
heroku logs --tail

# 4. Update passwords
# Go to https://your-app-name.herokuapp.com
# Change default passwords in Admin panel
```

---

## 🚂 Modern (Railway) - 8 minutes

```bash
# 1. Push to GitHub
git add .
git commit -m "Deploy to Railway"
git push origin main

# 2. Create Railway project
# Go to https://railway.app
# New Project → Deploy from GitHub → Select repo

# 3. Add environment variables
# In Railway dashboard: Variables
# Add: SMTP_PASSWORD = "your-password"

# 4. Done!
# Railway provides auto-deployed URL
```

---

## 🟦 Free Tier (Render) - 8 minutes

```bash
# 1. Push to GitHub (same as Railway)
git add .
git commit -m "Deploy to Render"
git push origin main

# 2. Create Render service
# Go to https://render.com
# New → Web Service → GitHub repo

# 3. Configure
# Build Command: pip install -r requirements.txt
# Start Command: streamlit run app.py --server.port 10000
# Add Variable: SMTP_PASSWORD = "your-password"

# 4. Deploy
# Click Deploy - usually live in 1-2 minutes
```

---

## 🐳 Docker (Any Platform) - 5 minutes

```bash
# Build image
docker build -t eneq-app .

# Run locally
docker run -p 8501:8501 -e SMTP_PASSWORD="test" eneq-app

# Or use Docker Compose
docker-compose up

# Push to Docker Hub
docker login
docker tag eneq-app username/eneq-app:latest
docker push username/eneq-app:latest

# Deploy to any platform using the image
```

---

## 🔒 Pre-Deployment Security Checklist

```bash
# 1. Change default passwords (CRITICAL!)
# After first login, go to Admin → Users
# Change all 3 default users' passwords

# 2. Set SMTP password securely
# Via environment variable (recommended):
export SMTP_PASSWORD="your-actual-password"

# Via Streamlit secrets:
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml with your password
# Never commit it!

# 3. Verify .gitignore
cat .gitignore | grep -E "secrets|settings|users"
# Should see:
# .streamlit/secrets.toml
# data/settings.json
# data/users.csv
```

---

## ✨ Post-Deployment

```bash
# 1. Test login
# Try all 3 roles with new passwords

# 2. Configure SMTP in UI
# Admin → Company & Email Settings
# Add your SMTP host, port, username

# 3. Test email
# Generate a quotation and send to yourself

# 4. Verify PDF generation
# Download a quote PDF and verify it looks good

# 5. Check data persistence
# If on Heroku/Render, verify data survives redeploy
```

---

## 🔧 Troubleshooting Quick Fixes

| Issue | Solution |
|-------|----------|
| App won't start | `heroku logs --tail` or check error logs |
| Email not working | Check SMTP host/port/username/password in Admin |
| Passwords stuck | Reset in Admin → Users tab |
| Data lost on deploy | Add persistent storage (see DEPLOYMENT_GUIDE.md) |
| App is slow | Upgrade to paid tier / check logs for bottlenecks |
| HTTPS not working | Auto-enabled on most platforms, try clearing cache |

---

## 📞 Support Resources

- **Streamlit Docs**: https://docs.streamlit.io/
- **Heroku Docs**: https://devcenter.heroku.com/
- **Railway Docs**: https://docs.railway.app/
- **Render Docs**: https://render.com/docs
- **Docker Docs**: https://docs.docker.com/

---

## 🎯 Recommended Path for Most Users

1. **Development**: Local with `streamlit run app.py`
2. **Testing**: Docker with `docker-compose up`
3. **Production**: Streamlit Cloud (easiest) or Railway (more features)

---

**Need detailed instructions?** See `DEPLOYMENT_GUIDE.md`  
**Full checklist?** See `DEPLOYMENT_CHECKLIST.md`
