#!/bin/bash

echo "🔧 Fixing Django admin CSS issue..."

# Navigate to project directory
cd /home/ubuntu/Labya_compute

# Pull latest changes
git pull origin backend-dev

# Activate virtual environment
cd backend
source venv/bin/activate

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Restart the backend service
echo "🔄 Restarting backend service..."
sudo systemctl restart labhya-compute

# Test nginx configuration and restart
echo "🌐 Restarting nginx..."
sudo nginx -t
sudo systemctl restart nginx

echo "✅ Django admin CSS fix deployed!"
echo "🌐 Admin panel: http://65.0.7.162/admin/"
