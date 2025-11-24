#!/bin/bash
# Quick Email Setup Script 📧

echo "🚀 QUICK EMAIL SETUP FOR RUBRIC APPROVAL SYSTEM"
echo "================================================"

echo ""
echo "Choose your email service:"
echo "1) Gmail (recommended for testing)"
echo "2) SendGrid (professional, free tier)"  
echo "3) Other SMTP service"
echo ""

read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "📧 GMAIL SETUP"
        echo "=============="
        echo ""
        echo "Steps to set up Gmail:"
        echo "1. Go to https://myaccount.google.com/security"
        echo "2. Enable 2-Factor Authentication if not already enabled"
        echo "3. Go to 'App passwords' and generate a new app password"
        echo "4. Use that app password (not your regular password)"
        echo ""
        
        read -p "📧 Enter your Gmail address: " gmail_user
        read -s -p "🔐 Enter your Gmail app password: " gmail_password
        echo ""
        
        # Set environment variables for this session
        export GMAIL_USER="$gmail_user"
        export GMAIL_APP_PASSWORD="$gmail_password"
        
        echo ""
        echo "✅ Gmail configuration set for this session!"
        echo "📧 User: $gmail_user"
        echo "🔐 Password: [HIDDEN]"
        echo ""
        echo "To make this permanent, add to your ~/.zshrc:"
        echo "export GMAIL_USER='$gmail_user'"
        echo "export GMAIL_APP_PASSWORD='$gmail_password'"
        ;;
        
    2)
        echo ""
        echo "📮 SENDGRID SETUP"
        echo "================="
        echo ""
        echo "Steps to set up SendGrid:"
        echo "1. Go to https://sendgrid.com and create free account"
        echo "2. Go to Settings > API Keys"
        echo "3. Create a new API Key with 'Mail Send' permissions"
        echo "4. Copy the API key"
        echo ""
        
        read -p "🔑 Enter your SendGrid API key: " sendgrid_key
        read -p "📧 Enter your from email address: " from_email
        
        # Set environment variables for this session
        export SENDGRID_API_KEY="$sendgrid_key"
        export FROM_EMAIL="$from_email"
        
        echo ""
        echo "✅ SendGrid configuration set for this session!"
        echo "📧 From: $from_email"
        echo "🔑 API Key: ${sendgrid_key:0:10}..."
        echo ""
        echo "To make this permanent, add to your ~/.zshrc:"
        echo "export SENDGRID_API_KEY='$sendgrid_key'"
        echo "export FROM_EMAIL='$from_email'"
        ;;
        
    3)
        echo ""
        echo "🌐 CUSTOM SMTP SETUP"
        echo "===================="
        echo ""
        
        read -p "📧 SMTP Host (e.g., smtp.gmail.com): " smtp_host
        read -p "🔌 SMTP Port (usually 587): " smtp_port
        read -p "👤 SMTP Username: " smtp_user
        read -s -p "🔐 SMTP Password: " smtp_password
        echo ""
        
        # Set environment variables for this session
        export SMTP_HOST="$smtp_host"
        export SMTP_PORT="$smtp_port"
        export SMTP_USER="$smtp_user"
        export SMTP_PASSWORD="$smtp_password"
        
        echo ""
        echo "✅ SMTP configuration set for this session!"
        echo "🌐 Host: $smtp_host:$smtp_port"
        echo "👤 User: $smtp_user"
        echo ""
        echo "To make this permanent, add to your ~/.zshrc:"
        echo "export SMTP_HOST='$smtp_host'"
        echo "export SMTP_PORT='$smtp_port'"
        echo "export SMTP_USER='$smtp_user'"
        echo "export SMTP_PASSWORD='$smtp_password'"
        ;;
        
    *)
        echo "❌ Invalid choice!"
        exit 1
        ;;
esac

echo ""
echo "🎯 Now you can send emails! Run:"
echo "python real_email_sender.py"
echo ""
echo "🔄 To reload environment in this terminal:"
echo "source ~/.zshrc"
