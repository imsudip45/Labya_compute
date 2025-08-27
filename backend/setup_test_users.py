#!/usr/bin/env python3
"""
Setup script for test users
Creates test renter and host accounts with money in their wallets
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
from api.models import Renter, Host, Wallet

def setup_test_users():
    """Create test users with wallets"""
    print("🔧 Setting up test users...")
    
    # Create test renter
    renter_email = "student@example.com"
    renter_password = "studentpass123"
    renter_name = "Test Student"
    
    if not User.objects.filter(email=renter_email).exists():
        user = User.objects.create_user(
            username=renter_email,
            email=renter_email,
            password=renter_password,
            first_name=renter_name
        )
        renter = Renter.objects.create(user=user)
        # Add money to wallet (auto-created by signal)
        renter.add_money(1000, "Initial deposit for testing")
        print(f"✅ Created renter: {renter_email} with 1000 NPR")
    else:
        user = User.objects.get(email=renter_email)
        renter = Renter.objects.get(user=user)
        # Add more money if needed
        wallet = renter.get_wallet()
        if wallet.balance < 500:
            renter.add_money(500, "Additional deposit for testing")
        print(f"✅ Renter exists: {renter_email} with {wallet.balance} NPR")
    
    # Create test host
    host_email = "host@example.com"
    host_password = "hostpass123"
    host_name = "Test Host"
    
    if not User.objects.filter(email=host_email).exists():
        user = User.objects.create_user(
            username=host_email,
            email=host_email,
            password=host_password,
            first_name=host_name
        )
        host = Host.objects.create(user=user)
        print(f"✅ Created host: {host_email}")
    else:
        print(f"✅ Host exists: {host_email}")
    
    print("\n📋 Test User Credentials:")
    print(f"   Renter: {renter_email} / {renter_password}")
    print(f"   Host: {host_email} / {host_password}")
    print(f"\n💰 Renter wallet balance: {renter.get_wallet().balance} NPR")

if __name__ == "__main__":
    setup_test_users()
