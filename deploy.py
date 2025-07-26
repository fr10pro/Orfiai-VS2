#!/usr/bin/env python3
"""
StreamHub Deployment Script
Automated deployment helper for Render hosting
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def check_requirements():
    """Check if all required files exist"""
    required_files = [
        "main.py",
        "models.py", 
        "database.py",
        "requirements.txt",
        "runtime.txt",
        "Procfile",
        "render.yaml",
        "gunicorn.conf.py"
    ]
    
    required_dirs = [
        "templates",
        "static/banners"
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    missing_dirs = []
    for directory in required_dirs:
        if not Path(directory).exists():
            missing_dirs.append(directory)
    
    if missing_files or missing_dirs:
        print("❌ Missing required files/directories:")
        for file in missing_files:
            print(f"   - {file}")
        for directory in missing_dirs:
            print(f"   - {directory}/")
        return False
    
    print("✅ All required files present")
    return True

def check_git_status():
    """Check git repository status"""
    try:
        # Check if git repo exists
        result = subprocess.run(["git", "status"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Not a git repository. Please initialize git first:")
            print("   git init")
            print("   git add .")
            print("   git commit -m 'Initial commit'")
            return False
        
        # Check for uncommitted changes
        if "nothing to commit" not in result.stdout:
            print("⚠️  Uncommitted changes detected:")
            print(result.stdout)
            return False
        
        print("✅ Git repository clean")
        return True
        
    except FileNotFoundError:
        print("❌ Git not found. Please install Git first.")
        return False

def validate_render_yaml():
    """Validate render.yaml configuration"""
    try:
        with open("render.yaml", "r") as f:
            content = f.read()
            
        # Basic validation
        required_sections = ["services", "- type: web", "- type: pserv"]
        for section in required_sections:
            if section not in content:
                print(f"❌ Missing section in render.yaml: {section}")
                return False
        
        print("✅ render.yaml configuration valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating render.yaml: {e}")
        return False

def create_deployment_guide():
    """Create deployment instructions"""
    guide = """
🚀 STREAMHUB DEPLOYMENT GUIDE
============================

Your StreamHub project is ready for deployment! Follow these steps:

OPTION 1: AUTOMATIC DEPLOYMENT (Recommended)
-------------------------------------------
1. Push your code to GitHub:
   git add .
   git commit -m "Ready for deployment"
   git push origin main

2. Go to https://render.com/deploy
3. Connect your GitHub repository
4. Render will automatically detect render.yaml
5. Click "Deploy" - Your app will be live in 5-10 minutes!

OPTION 2: MANUAL DEPLOYMENT
--------------------------
1. Create account at https://render.com
2. Create new "Web Service"
3. Connect your GitHub repository
4. Use these settings:
   - Name: streamhub
   - Environment: Python 3
   - Build Command: pip install -r requirements.txt
   - Start Command: gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT

5. Create PostgreSQL database:
   - Go to Dashboard → New → PostgreSQL
   - Name: streamhub-db
   - Connect to your web service

6. Your app will be available at:
   https://your-app-name.onrender.com/

IMPORTANT NOTES:
===============
- Database will be automatically connected
- File uploads will work out of the box
- HTTPS is enabled by default
- Health checks are configured
- Logs are available in Render dashboard

ESTIMATED DEPLOYMENT TIME: 5-10 minutes
ESTIMATED COST: $14/month (Starter plan + PostgreSQL)

For detailed instructions, see README.md
"""
    
    with open("DEPLOYMENT_GUIDE.txt", "w") as f:
        f.write(guide)
    
    print("✅ Deployment guide created: DEPLOYMENT_GUIDE.txt")

def main():
    """Main deployment preparation function"""
    print("🎬 StreamHub Deployment Preparation")
    print("=" * 50)
    
    # Check all requirements
    checks = [
        ("Checking required files...", check_requirements),
        ("Validating render.yaml...", validate_render_yaml),
        ("Checking git status...", check_git_status),
    ]
    
    all_passed = True
    for description, check_func in checks:
        print(f"\n{description}")
        if not check_func():
            all_passed = False
    
    # Create deployment guide
    print("\nCreating deployment guide...")
    create_deployment_guide()
    
    # Final status
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 READY FOR DEPLOYMENT!")
        print("\nNext steps:")
        print("1. Push your code to GitHub")
        print("2. Go to https://render.com/deploy")
        print("3. Connect your repository")
        print("4. Deploy!")
        print("\n📖 See DEPLOYMENT_GUIDE.txt for detailed instructions")
    else:
        print("❌ Please fix the issues above before deploying")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
