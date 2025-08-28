#!/bin/bash

echo "🧪 Testing Django Backend Connection"
echo "==================================="

# Check if Django service is running
echo "1. Django service status:"
sudo systemctl is-active labhya-compute

echo ""
echo "2. Django service logs (last 10 lines):"
sudo journalctl -u labhya-compute --no-pager -n 10

echo ""
echo "3. Checking if port 8000 is listening:"
sudo netstat -tlnp | grep :8000

echo ""
echo "4. Testing Django backend directly:"
timeout 10s curl -v http://localhost:8000/admin/ 2>&1 | head -10

echo ""
echo "5. Checking gunicorn processes:"
ps aux | grep gunicorn | grep -v grep

echo ""
echo "6. Testing with different timeout:"
curl --connect-timeout 5 --max-time 10 http://localhost:8000/admin/ 2>&1 | head -5

echo ""
echo "7. Checking Django configuration:"
cd /home/ubuntu/Labya_compute/backend
source venv/bin/activate
python manage.py check 2>&1

echo ""
echo "8. Testing database connection:"
python manage.py dbshell -c "SELECT 1;" 2>/dev/null && echo "✅ Database OK" || echo "❌ Database connection failed"