#!/usr/bin/env python3
"""
Debug script to check renters endpoint
"""

import requests
import json

API_BASE = "http://localhost:8000/api"

def debug_renters():
    """Debug the renters endpoint"""
    print("🔍 Debugging renters endpoint...")
    
    # Login first
    login_data = {
        "username": "student@example.com",
        "password": "studentpass123"
    }
    
    try:
        resp = requests.post(f"{API_BASE}/auth/login/", json=login_data, timeout=30)
        if not resp.ok:
            print(f"❌ Login failed: {resp.status_code}")
            return
        
        data = resp.json()
        token = data["access"]
        headers = {"Authorization": f"Bearer {token}"}
        
        print(f"✅ Login successful")
        
        # Test renters endpoint
        print("\nTesting /renters/ endpoint...")
        renters_resp = requests.get(f"{API_BASE}/renters/", headers=headers, timeout=30)
        print(f"Status code: {renters_resp.status_code}")
        print(f"Response: {renters_resp.text}")
        
        if renters_resp.ok:
            renters = renters_resp.json()
            print(f"Renters data: {json.dumps(renters, indent=2)}")
            
            if isinstance(renters, list) and len(renters) > 0:
                print(f"✅ Found {len(renters)} renter(s)")
                print(f"First renter ID: {renters[0].get('id', 'N/A')}")
            else:
                print("❌ No renters found or unexpected format")
        
        # Test hosts endpoint
        print("\nTesting /hosts/ endpoint...")
        hosts_resp = requests.get(f"{API_BASE}/hosts/", headers=headers, timeout=30)
        print(f"Status code: {hosts_resp.status_code}")
        print(f"Response: {hosts_resp.text}")
        
        if hosts_resp.ok:
            hosts = hosts_resp.json()
            print(f"Hosts data: {json.dumps(hosts, indent=2)}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_renters()
