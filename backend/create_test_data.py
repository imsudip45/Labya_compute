#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'labhya_compute.settings')
django.setup()

from django.contrib.auth.models import User
from api.models import Renter, Host, GPU, Wallet, Transaction
from django.utils import timezone

def create_test_data():
    print("Creating test data...")
    
    # Create test users
    try:
        # Create host user
        host_user = User.objects.create_user(
            username='host@test.com',
            email='host@test.com',
            password='testpass123',
            first_name='John',
            last_name='Host'
        )
        host = Host.objects.create(user=host_user)
        print(f"Created host: {host_user.email}")
        
        # Create renter user
        renter_user = User.objects.create_user(
            username='renter@test.com',
            email='renter@test.com',
            password='testpass123',
            first_name='Alice',
            last_name='Renter'
        )
        renter = Renter.objects.create(user=renter_user)
        print(f"Created renter: {renter_user.email}")
        
        # Add money to renter wallet
        renter.add_money(1000, "Initial deposit")
        print(f"Added 1000 to renter wallet")
        
        # Create GPUs for host
        gpu1 = GPU.objects.create(
            host=host,
            gpu_name="NVIDIA RTX 4090",
            gpu_model="RTX 4090",
            gpu_memory=24,
            gpu_price=250,
            gpu_location="Kathmandu, Nepal",
            gpu_availability=True
        )
        print(f"Created GPU: {gpu1.gpu_name}")
        
        gpu2 = GPU.objects.create(
            host=host,
            gpu_name="NVIDIA RTX 4080",
            gpu_model="RTX 4080",
            gpu_memory=16,
            gpu_price=180,
            gpu_location="Pokhara, Nepal",
            gpu_availability=True
        )
        print(f"Created GPU: {gpu2.gpu_name}")
        
        print("\nTest data created successfully!")
        print("\nTest credentials:")
        print("Host: host@test.com / testpass123")
        print("Renter: renter@test.com / testpass123")
        
    except Exception as e:
        print(f"Error creating test data: {e}")

if __name__ == '__main__':
    create_test_data()
