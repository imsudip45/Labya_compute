#!/usr/bin/env python3
"""
Test script for the relay system
Tests session creation, port allocation, and connection info
"""

import requests
import json
import time
from datetime import datetime, timedelta

# Configuration
API_BASE = "http://localhost:8000/api"
RENTER_EMAIL = "student@example.com"
RENTER_PASSWORD = "studentpass123"
HOST_EMAIL = "host@example.com"
HOST_PASSWORD = "hostpass123"

def http(method, path, **kwargs):
    """Helper function for HTTP requests"""
    url = f"{API_BASE.rstrip('/')}/{path.lstrip('/')}"
    print(f"[HTTP] {method.upper()} {path}")
    return requests.request(method, url, timeout=30, **kwargs)

def login(email, password):
    """Login and get JWT token"""
    resp = http("post", "/auth/login/", json={"username": email, "password": password})
    resp.raise_for_status()
    data = resp.json()
    return data["access"], data.get("refresh", "")

def test_relay_system():
    """Test the complete relay system flow"""
    print("🧪 Testing Relay System")
    print("=" * 50)
    
    # 1. Login as renter
    print("\n1. Logging in as renter...")
    renter_token, _ = login(RENTER_EMAIL, RENTER_PASSWORD)
    renter_headers = {"Authorization": f"Bearer {renter_token}"}
    
    # 2. Get available GPUs
    print("\n2. Getting available GPUs...")
    gpus_resp = http("get", "/gpus/available/", headers=renter_headers)
    gpus_resp.raise_for_status()
    gpus = gpus_resp.json()
    
    if not gpus:
        print("❌ No available GPUs found")
        return
    
    gpu = gpus[0]
    print(f"✅ Found GPU: {gpu['gpu_name']} (ID: {gpu['id']})")
    
    # 3. Get renter and host info
    print("\n3. Getting user info...")
    renter_resp = http("get", "/renters/", headers=renter_headers)
    renter_resp.raise_for_status()
    renters_data = renter_resp.json()
    renters = renters_data.get("results", renters_data)  # Handle pagination
    renter_id = renters[0]["id"]
    
    # Get host info from GPU
    host_id = gpu["host"]
    
    print(f"✅ Renter ID: {renter_id}")
    print(f"✅ Host ID: {host_id}")
    
    # 4. Create a session
    print("\n4. Creating session...")
    session_data = {
        "gpu": gpu["id"],
        "renter": renter_id,
        "host": host_id,
        "start_time": datetime.now().isoformat(),
        "ssh_host": "localhost",  # This will be overridden by the backend
        "ssh_port": 22,  # This will be overridden by the backend
        "ssh_username": "test_user",  # This will be overridden by the backend
        "ssh_password": "test_pass123",
        "is_auto_reconnect": True
    }
    
    session_resp = http("post", "/sessions/", json=session_data, headers=renter_headers)
    session_resp.raise_for_status()
    session = session_resp.json()
    session_id = session["id"]
    
    print(f"✅ Session created: {session_id}")
    print(f"   SSH Host: {session['ssh_host']}")
    print(f"   SSH Port: {session['ssh_port']}")
    print(f"   SSH Username: {session['ssh_username']}")
    
    # 5. Get connection info
    print("\n5. Getting connection info...")
    conn_resp = http("get", f"/sessions/{session_id}/connection_info/", headers=renter_headers)
    conn_resp.raise_for_status()
    conn_info = conn_resp.json()
    
    print(f"✅ Connection Info:")
    print(f"   SSH Command: {conn_info['ssh_connection_string']}")
    print(f"   Connection Status: {conn_info['connection_status']}")
    print(f"   Is Connected: {conn_info['is_connected']}")
    
    # 6. Test session detail
    print("\n6. Getting session details...")
    detail_resp = http("get", f"/sessions/{session_id}/", headers=renter_headers)
    detail_resp.raise_for_status()
    detail = detail_resp.json()
    
    print(f"✅ Session Details:")
    print(f"   Status: {detail['status']}")
    print(f"   Total Cost: {detail['total_cost']}")
    print(f"   Session Duration: {detail['session_duration']} hours")
    print(f"   SSH Connection String: {detail['ssh_connection_string']}")
    
    # 7. Check relay port allocation
    print("\n7. Checking relay port allocation...")
    # This would require admin access to check RelayPort model directly
    # For now, we'll just verify the session has relay info
    if detail['ssh_host'] and detail['ssh_port']:
        print(f"✅ Relay port allocated: {detail['ssh_host']}:{detail['ssh_port']}")
    else:
        print("❌ No relay port allocated")
    
    # 8. End the session
    print("\n8. Ending session...")
    end_resp = http("post", f"/sessions/{session_id}/end_session/", headers=renter_headers)
    end_resp.raise_for_status()
    end_result = end_resp.json()
    
    print(f"✅ Session ended:")
    print(f"   Total Cost: {end_result['total_cost']}")
    print(f"   Session ID: {end_result['session_id']}")
    
    print("\n🎉 Relay system test completed successfully!")

if __name__ == "__main__":
    try:
        test_relay_system()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
