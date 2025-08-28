#!/bin/bash

# Labya Compute EC2 Deployment Script
set -e

echo "🚀 Starting Labya Compute deployment..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo "🔧 Installing dependencies..."
sudo apt install -y python3 python3-pip python3-venv nodejs npm docker.io docker-compose openssh-server postgresql postgresql-contrib nginx git curl

# Start and enable services
echo "🔌 Starting services..."
sudo systemctl start docker
sudo systemctl enable docker
sudo systemctl start ssh
sudo systemctl enable ssh
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Add user to docker group
sudo usermod -aG docker $USER

# Configure PostgreSQL
echo "🗄️ Configuring PostgreSQL..."
sudo -u postgres psql -c "CREATE DATABASE labhya_compute;" || echo "Database already exists"
sudo -u postgres psql -c "CREATE USER labhya_user WITH PASSWORD 'labhya_secure_2024';" || echo "User already exists"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE labhya_compute TO labhya_user;"

# Configure SSH for relay
echo "🔐 Configuring SSH for relay..."
sudo sed -i 's/#GatewayPorts no/GatewayPorts yes/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Setup backend
echo "🐍 Setting up Python backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
echo "🗃️ Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser (optional)
echo "👤 Creating superuser..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@labhya.com', 'admin123') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell

# Setup frontend
echo "⚛️ Setting up React frontend..."
cd ../frontend
npm install
npm run build

# Configure Nginx
echo "🌐 Configuring Nginx..."
sudo cp ../backend/nginx.conf /etc/nginx/sites-available/labhya-compute
sudo ln -sf /etc/nginx/sites-available/labhya-compute /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# Create systemd service for backend
echo "🔧 Creating systemd service..."
sudo tee /etc/systemd/system/labhya-compute.service > /dev/null <<EOF
[Unit]
Description=Labya Compute Backend
After=network.target

[Service]
Type=exec
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/Labya_compute/backend
Environment=PATH=/home/ubuntu/Labya_compute/backend/venv/bin
ExecStart=/home/ubuntu/Labya_compute/backend/venv/bin/gunicorn -c gunicorn.conf.py labhya_compute.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start backend service
sudo systemctl daemon-reload
sudo systemctl enable labhya-compute
sudo systemctl start labhya-compute

echo "✅ Deployment completed!"
echo "🌐 Frontend: http://65.0.7.162"
echo "🔌 Backend API: http://65.0.7.162/api/"
echo "👤 Admin: http://65.0.7.162/admin/ (admin/admin123)"
echo "🔐 SSH Relay: 65.0.7.162:22"
