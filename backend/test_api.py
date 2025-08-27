#!/usr/bin/env python
import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_api():
    print("Testing API endpoints...")
    
    # Test login
    print("\n1. Testing login...")
    login_data = {
        "email": "host@test.com",
        "password": "testpass123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login/", json=login_data)
        print(f"Login status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Login successful: {data.get('access', 'No access token')[:20]}...")
            token = data['access']
        else:
            print(f"Login failed: {response.text}")
            return
    except Exception as e:
        print(f"Login error: {e}")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Test get GPUs
    print("\n2. Testing get GPUs...")
    try:
        response = requests.get(f"{BASE_URL}/gpus/", headers=headers)
        print(f"GPUs status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response type: {type(data)}")
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            # Handle paginated response
            if isinstance(data, dict) and 'results' in data:
                gpus = data['results']
                print(f"Found {len(gpus)} GPUs (paginated)")
            else:
                gpus = data
                print(f"Found {len(gpus)} GPUs (direct)")
            
            for gpu in gpus:
                print(f"  - {gpu.get('gpu_name', 'Unknown')} (${gpu.get('gpu_price', 0)}/hour)")
        else:
            print(f"GPUs failed: {response.text}")
    except Exception as e:
        print(f"GPUs error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test get wallet
    print("\n3. Testing get wallet...")
    try:
        response = requests.get(f"{BASE_URL}/wallets/", headers=headers)
        print(f"Wallet status: {response.status_code}")
        if response.status_code == 200:
            wallet = response.json()
            print(f"Wallet balance: ${wallet['balance']}")
        else:
            print(f"Wallet failed: {response.text}")
    except Exception as e:
        print(f"Wallet error: {e}")
    
    # Test get dashboard stats
    print("\n4. Testing dashboard stats...")
    try:
        response = requests.get(f"{BASE_URL}/dashboard/stats/", headers=headers)
        print(f"Stats status: {response.status_code}")
        if response.status_code == 200:
            stats = response.json()
            print(f"Dashboard stats: {stats}")
        else:
            print(f"Stats failed: {response.text}")
    except Exception as e:
        print(f"Stats error: {e}")
    
    # Test get sessions
    print("\n5. Testing get sessions...")
    try:
        response = requests.get(f"{BASE_URL}/sessions/", headers=headers)
        print(f"Sessions status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response type: {type(data)}")
            
            # Handle paginated response
            if isinstance(data, dict) and 'results' in data:
                sessions = data['results']
                print(f"Found {len(sessions)} sessions (paginated)")
            else:
                sessions = data
                print(f"Found {len(sessions)} sessions (direct)")
        else:
            print(f"Sessions failed: {response.text}")
    except Exception as e:
        print(f"Sessions error: {e}")
    
    print("\nAPI test completed!")

if __name__ == '__main__':
    test_api()
