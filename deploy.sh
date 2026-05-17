#!/bin/bash

# ENEQ Quotation Generator - Quick Deployment Script
# This script helps with local deployment testing

set -e

echo "🚀 ENEQ Quotation Generator - Deployment Helper"
echo "=================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker not found. Installing Docker is recommended for containerized deployment."
    echo "Get Docker: https://www.docker.com/products/docker-desktop"
fi

# Menu
echo ""
echo "Select deployment method:"
echo "1. Run locally (development)"
echo "2. Run with Docker (testing)"
echo "3. Prepare for Heroku deployment"
echo "4. Prepare for Streamlit Cloud deployment"
echo "5. Prepare for Railway deployment"
echo ""
read -p "Enter choice (1-5): " choice

case $choice in
    1)
        echo "🔧 Setting up local development..."
        echo ""
        
        # Check Python version
        if ! command -v python3 &> /dev/null; then
            echo "❌ Python 3 not found. Please install Python 3.9+"
            exit 1
        fi
        
        echo "✅ Python 3 found: $(python3 --version)"
        
        # Create virtual environment
        if [ ! -d "venv" ]; then
            echo "📦 Creating virtual environment..."
            python3 -m venv venv
        fi
        
        # Activate virtual environment
        source venv/bin/activate
        
        # Install dependencies
        echo "📚 Installing dependencies..."
        pip install -r requirements.txt
        
        echo ""
        echo "✅ Setup complete!"
        echo ""
        echo "🚀 To run the app, execute:"
        echo "   source venv/bin/activate"
        echo "   streamlit run app.py"
        echo ""
        echo "📝 Before first run, change default passwords in Admin panel"
        echo "📧 Configure SMTP in Admin > Company & Email Settings"
        ;;
        
    2)
        echo "🐳 Setting up Docker..."
        echo ""
        
        # Check Docker
        if ! command -v docker &> /dev/null; then
            echo "❌ Docker not found. Please install Docker Desktop."
            exit 1
        fi
        
        echo "✅ Docker found: $(docker --version)"
        
        # Check docker-compose
        if ! command -v docker-compose &> /dev/null; then
            echo "❌ Docker Compose not found. Please install Docker Compose."
            exit 1
        fi
        
        echo "✅ Docker Compose found: $(docker-compose --version)"
        
        # Get SMTP password
        echo ""
        read -sp "Enter SMTP password (or press Enter to skip): " smtp_password
        echo ""
        
        # Build and run
        if [ -z "$smtp_password" ]; then
            echo "📦 Building Docker image (without SMTP password)..."
            docker-compose build
            docker-compose up
        else
            echo "📦 Building Docker image (with SMTP password)..."
            SMTP_PASSWORD="$smtp_password" docker-compose build
            SMTP_PASSWORD="$smtp_password" docker-compose up
        fi
        
        echo "✅ App running at http://localhost:8501"
        ;;
        
    3)
        echo "🟣 Preparing for Heroku deployment..."
        echo ""
        
        # Check git
        if ! command -v git &> /dev/null; then
            echo "❌ Git not found. Please install Git."
            exit 1
        fi
        
        # Check Heroku CLI
        if ! command -v heroku &> /dev/null; then
            echo "⚠️  Heroku CLI not found. Install from: https://devcenter.heroku.com/articles/heroku-cli"
            echo ""
        fi
        
        echo "✅ Files needed for Heroku deployment:"
        echo "   ✓ Procfile (already created)"
        echo "   ✓ requirements.txt (already exists)"
        echo "   ✓ Dockerfile (already created)"
        echo ""
        echo "📋 Next steps:"
        echo "   1. heroku login"
        echo "   2. heroku create your-app-name"
        echo "   3. heroku config:set SMTP_PASSWORD='your-password'"
        echo "   4. git push heroku main"
        echo "   5. heroku logs --tail"
        echo ""
        echo "📖 More info: see DEPLOYMENT_GUIDE.md"
        ;;
        
    4)
        echo "☁️  Preparing for Streamlit Cloud deployment..."
        echo ""
        
        # Check git
        if ! command -v git &> /dev/null; then
            echo "❌ Git not found. Please install Git."
            exit 1
        fi
        
        echo "✅ Files needed for Streamlit Cloud deployment:"
        echo "   ✓ requirements.txt (already exists)"
        echo "   ✓ .streamlit/secrets.toml.example (already created)"
        echo ""
        echo "📋 Next steps:"
        echo "   1. Commit all changes: git add . && git commit -m 'Deploy'"
        echo "   2. Push to GitHub: git push origin main"
        echo "   3. Go to https://share.streamlit.io"
        echo "   4. Deploy from your GitHub repository"
        echo "   5. Add secrets in app settings"
        echo ""
        echo "📖 More info: see DEPLOYMENT_GUIDE.md"
        ;;
        
    5)
        echo "🚂 Preparing for Railway deployment..."
        echo ""
        
        # Check git
        if ! command -v git &> /dev/null; then
            echo "❌ Git not found. Please install Git."
            exit 1
        fi
        
        echo "✅ Files ready for Railway deployment:"
        echo "   ✓ requirements.txt (already exists)"
        echo "   ✓ Procfile (already created)"
        echo "   ✓ Dockerfile (already created)"
        echo ""
        echo "📋 Next steps:"
        echo "   1. Commit all changes: git add . && git commit -m 'Deploy'"
        echo "   2. Push to GitHub: git push origin main"
        echo "   3. Go to https://railway.app"
        echo "   4. Create new project from GitHub"
        echo "   5. Add environment variables in Railway dashboard"
        echo ""
        echo "📖 More info: see DEPLOYMENT_GUIDE.md"
        ;;
        
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✅ Deployment preparation complete!"
