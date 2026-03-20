import requests
import json
import time

def test_performance():
    url = "http://localhost:8000/api/schedule"
    payload = {
        "candidates": [
            { "name": "Alice Chen", "availability": "Tue-Thu 2-5 PM" },
            { "name": "Bob Smith", "availability": "Mon/Wed 9 AM - 12 PM" },
            { "name": "Charlie Day", "availability": "Every Friday morning" },
            { "name": "Diana Prince", "availability": "Weekday afternoons 3-5 PM" },
            { "name": "Ethan Hunt", "availability": "Monday all day" }
        ],
        "interviewers": [
            { "name": "Dr. Aris", "availability": "Tue 10 AM-4 PM, Wed 10 AM-4 PM" },
            { "name": "Sarah Connor", "availability": "Wed-Fri 9 AM-12 PM" },
            { "name": "Tony Stark", "availability": "Mon 2-6 PM, Thu 2-6 PM" },
            { "name": "Bruce Wayne", "availability": "Mon-Fri 9-11 AM" },
            { "name": "Ellen Ripley", "availability": "Every Tuesday afternoon" }
        ],
        "duration": 60
    }

    print("🚀 Running E2E Performance Benchmark...")
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, timeout=20)
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
        
    duration = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Response time: {duration:.2f}s")
        print(f"📅 Scheduled {len(data['assignments'])} assignments.")
        print(f"🚨 Unassigned: {len(data['unassigned'])}")
    else:
        print(f"❌ Request failed ({response.status_code}): {response.text}")

if __name__ == "__main__":
    test_performance()
