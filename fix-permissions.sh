#!/bin/bash

echo "🔧 Fixing file permissions for Django admin CSS..."

# Navigate to project directory
cd /home/ubuntu/Labya_compute

# Check current permissions
echo "📁 Current permissions:"
ls -la backend/staticfiles/
echo ""

# Fix ownership and permissions for static files
echo "📁 Fixing static files permissions..."
sudo chown -R www-data:www-data backend/staticfiles
sudo chmod -R 755 backend/staticfiles

# Fix permissions for the entire backend directory path
echo "📁 Fixing backend directory permissions..."
sudo chown -R ubuntu:ubuntu backend/
sudo chmod -R 755 backend/

# Ensure nginx can read the static files directory
echo "🔐 Setting specific permissions for nginx..."
sudo chmod 755 /home/ubuntu/Labya_compute
sudo chmod 755 /home/ubuntu/Labya_compute/backend
sudo chmod 755 /home/ubuntu/Labya_compute/backend/staticfiles

# Check nginx user and group
echo "👤 Nginx user info:"
ps aux | grep nginx | head -1
echo ""

# Verify permissions after fix
echo "📁 Permissions after fix:"
ls -la backend/staticfiles/
echo ""

# Test if nginx can access the files
echo "🧪 Testing nginx access..."
sudo -u www-data test -r backend/staticfiles/admin/css/base.css && echo "✅ Nginx can read base.css" || echo "❌ Nginx cannot read base.css"

# Restart nginx to ensure changes take effect
echo "🔄 Restarting nginx..."
sudo systemctl restart nginx

# Test nginx configuration
echo "✅ Testing nginx configuration..."
sudo nginx -t

# Check nginx error logs
echo "📋 Recent nginx error logs:"
sudo tail -5 /var/log/nginx/error.log

echo ""
echo "✅ Permissions fix completed!"
echo "🌐 Admin panel: http://65.0.7.162/admin/"
echo "📁 Static files: http://65.0.7.162/static/admin/css/base.css"
echo ""
echo "💡 If still getting 403 errors, try:"
echo "   1. Clear browser cache (Ctrl+F5)"
echo "   2. Check nginx error logs: sudo tail -f /var/log/nginx/error.log"
echo "   3. Test static file directly in browser"
