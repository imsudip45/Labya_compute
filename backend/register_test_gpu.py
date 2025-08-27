#!/usr/bin/env python3
"""
Register a test GPU for the host user
"""

import os
import sys
import django

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'labhya_compute.settings')
django.setup()

from django.contrib.auth.models import User
from api.models import Host, GPU

def register_test_gpu():
    """Register a test GPU for the host"""
    print("🔧 Registering test GPU...")
    
    # Get the test host
    host_email = "host@example.com"
    try:
        user = User.objects.get(email=host_email)
        host = Host.objects.get(user=user)
    except (User.DoesNotExist, Host.DoesNotExist):
        print(f"❌ Host {host_email} not found. Run setup_test_users.py first.")
        return
    
    # Check if GPU already exists
    existing_gpus = GPU.objects.filter(host=host)
    if existing_gpus.exists():
        print(f"✅ Host already has {existing_gpus.count()} GPU(s):")
        for gpu in existing_gpus:
            print(f"   - {gpu.gpu_name} ({gpu.gpu_memory}GB, {gpu.gpu_price} NPR/hour)")
        return
    
    # Create a test GPU
    gpu = GPU.objects.create(
        host=host,
        gpu_name="NVIDIA RTX 4090",
        gpu_model="RTX 4090",
        gpu_memory=24,
        gpu_price=100,  # 100 NPR per hour
        gpu_availability=True,
        gpu_location="Test Location"
    )
    
    print(f"✅ Created test GPU:")
    print(f"   Name: {gpu.gpu_name}")
    print(f"   Memory: {gpu.gpu_memory}GB")
    print(f"   Price: {gpu.gpu_price} NPR/hour")
    print(f"   Available: {gpu.gpu_availability}")

if __name__ == "__main__":
    register_test_gpu()
