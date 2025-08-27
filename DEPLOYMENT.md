# Labya Compute EC2 Deployment Guide

## Prerequisites
- AWS EC2 instance (Ubuntu 22.04 LTS recommended)
- Security group configured with required ports
- SSH access to the instance

## Security Group Configuration

### Inbound Rules:
- **SSH (22)**: 0.0.0.0/0 (or your IP for security)
- **HTTP (80)**: 0.0.0.0/0
- **HTTPS (443)**: 0.0.0.0/0 (if using SSL)
- **Custom TCP (8000)**: 0.0.0.0/0 (Django backend)
- **Custom TCP (8001-8010)**: 0.0.0.0/0 (Relay SSH ports)

## Quick Deployment

1. **Connect to your EC2 instance:**
   ```bash
   ssh -i "your-key.pem" ubuntu@65.0.7.162
   ```

2. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd Labya_compute
   ```

3. **Make deployment script executable and run:**
   ```bash
   chmod +x backend/deploy.sh
   ./backend/deploy.sh
   ```

## Manual Deployment Steps

If you prefer to run commands manually:

### 1. Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Dependencies
```bash
sudo apt install -y python3 python3-pip python3-venv nodejs npm docker.io docker-compose openssh-server postgresql postgresql-contrib nginx git curl
```

### 3. Configure PostgreSQL
```bash
sudo -u postgres psql -c "CREATE DATABASE labhya_compute;"
sudo -u postgres psql -c "CREATE USER labhya_user WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE labhya_compute TO labhya_user;"
```

### 4. Configure SSH for Relay
```bash
sudo sed -i 's/#GatewayPorts no/GatewayPorts yes/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

### 5. Setup Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
```

### 6. Setup Frontend
```bash
cd ../frontend
npm install
npm run build
```

### 7. Configure Nginx
```bash
sudo cp backend/nginx.conf /etc/nginx/sites-available/labhya-compute
sudo ln -sf /etc/nginx/sites-available/labhya-compute /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 8. Start Backend Service
```bash
sudo systemctl enable labhya-compute
sudo systemctl start labhya-compute
```

## Access URLs

- **Frontend**: http://65.0.7.162
- **Backend API**: http://65.0.7.162/api/
- **Admin Panel**: http://65.0.7.162/admin/ (admin/admin123)
- **SSH Relay**: 65.0.7.162:22

## Important Notes

1. **Database Password**: Change the default password in `backend/labhya_compute/settings.py`
2. **Secret Key**: Generate a new Django secret key for production
3. **SSL**: Consider setting up HTTPS with Let's Encrypt
4. **Backups**: Set up regular database backups
5. **Monitoring**: Use CloudWatch for monitoring

## Troubleshooting

### Check Service Status
```bash
sudo systemctl status labhya-compute
sudo systemctl status nginx
sudo systemctl status postgresql
```

### View Logs
```bash
sudo journalctl -u labhya-compute -f
sudo tail -f /var/log/nginx/error.log
```

### Test API
```bash
curl http://65.0.7.162/api/health/
```

## Agent Configuration

Update your local agent to connect to the EC2 instance:
- API Base URL: `http://65.0.7.162:8000/api`
- Relay Host: `65.0.7.162`
