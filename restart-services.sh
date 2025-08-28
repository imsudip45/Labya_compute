#!/bin/bash

echo "🔄 Restarting services to fix 502 Bad Gateway..."

# Stop services
echo "🛑 Stopping services..."
sudo systemctl stop labhya-compute
sudo systemctl stop nginx

# Wait a moment
sleep 2

# Start Django backend
echo "🐍 Starting Django backend..."
sudo systemctl start labhya-compute
sleep 3

# Check if Django is running
if sudo systemctl is-active --quiet labhya-compute; then
    echo "✅ Django backend is running"
else
    echo "❌ Django backend failed to start"
    echo "📋 Django logs:"
    sudo journalctl -u labhya-compute --no-pager -n 10
    exit 1
fi

# Start nginx
echo "🌐 Starting nginx..."
sudo systemctl start nginx

# Check if nginx is running
if sudo systemctl is-active --quiet nginx; then
    echo "✅ Nginx is running"
else
    echo "❌ Nginx failed to start"
    exit 1
fi

# Test the connection
echo "🧪 Testing connection..."
sleep 2
curl -I http://localhost:8000/api/ 2>/dev/null && echo "✅ Django backend responding" || echo "❌ Django backend not responding"

echo ""
echo "✅ Services restarted!"
echo "🌐 Frontend: http://65.0.7.162"
echo "🔌 Backend API: http://65.0.7.162/api/"
echo "👤 Admin: http://65.0.7.162/admin/"
