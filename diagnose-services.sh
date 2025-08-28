#!/bin/bash

echo "🔍 Diagnosing service issues..."

# Check if Django backend service is running
echo "🐍 Checking Django backend service..."
sudo systemctl status labhya-compute --no-pager

echo ""
echo "📋 Django service logs (last 10 lines):"
sudo journalctl -u labhya-compute --no-pager -n 10

echo ""
echo "🌐 Checking nginx status..."
sudo systemctl status nginx --no-pager

echo ""
echo "🔌 Checking if port 8000 is listening..."
sudo netstat -tlnp | grep :8000

echo ""
echo "📋 Nginx error logs (last 10 lines):"
sudo tail -10 /var/log/nginx/error.log

echo ""
echo "📋 Nginx access logs (last 5 lines):"
sudo tail -5 /var/log/nginx/access.log

echo ""
echo "🧪 Testing Django backend directly..."
curl -I http://localhost:8000/api/ 2>/dev/null || echo "❌ Django backend not responding on localhost:8000"

echo ""
echo "🔧 Quick fixes to try:"
echo "1. Restart Django service: sudo systemctl restart labhya-compute"
echo "2. Restart nginx: sudo systemctl restart nginx"
echo "3. Check Django logs: sudo journalctl -u labhya-compute -f"
