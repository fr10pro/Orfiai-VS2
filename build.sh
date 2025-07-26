#!/bin/bash

# StreamHub Build Script for Render
echo "🎬 Building StreamHub for Render..."

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p static/banners
mkdir -p templates

# Set permissions
echo "🔒 Setting permissions..."
chmod -R 755 static/
chmod +x build.sh

# Database setup (migrations will run automatically via init_db)
echo "🗄️  Database setup ready..."

echo "✅ Build completed successfully!"
echo "🚀 StreamHub is ready for deployment!"
