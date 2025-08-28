#!/bin/bash

echo "🔍 Debugging 502 Bad Gateway Issue"
echo "=================================="

# Test Django backend directly
echo "1. Testing Django backend on port 8000..."
curl -v http://localhost:8000/admin/ 2>&1 | head -20

echo ""
echo "2. Testing Django API on port 8000..."
curl -v http://localhost:8000/api/ 2>&1 | head -20

echo ""
echo "3. Checking if port 8000 is listening..."
sudo netstat -tlnp | grep :8000

echo ""
echo "4. Checking nginx configuration..."
sudo cat /etc/nginx/sites-enabled/labhya-compute

echo ""
echo "5. Checking nginx error logs..."
sudo tail -10 /var/log/nginx/error.log

echo ""
echo "6. Testing nginx proxy to Django..."
curl -v http://localhost/api/ 2>&1 | head -20

echo ""
echo "7. Checking frontend files..."
ls -la /home/ubuntu/Labya_compute/frontend/dist/

echo ""
echo "8. Testing frontend directly..."
curl -I http://localhost/ 2>/dev/null || echo "Frontend not responding"

echo ""
echo "🔧 Potential Issues:"
echo "==================="
echo "1. Django backend might not be responding on localhost:8000"
echo "2. Nginx configuration might be incorrect"
echo "3. Firewall or security group blocking connections"
echo "4. Django service might have crashed after restart"
