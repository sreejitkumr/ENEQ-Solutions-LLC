#!/bin/bash

# ENEQ Quotation Generator - Local Development Runner

echo "🚀 ENEQ Quotation Generator - Local Development Server"
echo "========================================================"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate virtual environment
echo "📦 Activating virtual environment..."
source "$SCRIPT_DIR/venv/bin/activate"

# Set environment variables (optional)
# Uncomment and fill in your SMTP password if testing email:
# export SMTP_PASSWORD="your-smtp-password-here"

echo "✅ Virtual environment activated"
echo ""

# Display login credentials
echo "📋 Default Login Credentials:"
echo "   Admin:  admin / Adm!n2024#Secure"
echo "   Sales:  sales / S@les2024#Secure"
echo "   Viewer: viewer / View2024#Secure"
echo ""
echo "⚠️  Important: Change these passwords after first login!"
echo ""

# Run the Streamlit app
echo "🌐 Starting Streamlit application..."
echo "   App will be available at: http://localhost:8501"
echo ""
echo "💡 Tip: Press CTRL+C to stop the server"
echo ""

streamlit run app.py
