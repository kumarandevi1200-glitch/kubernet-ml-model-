import urllib.request
import json
import random
import time

print("Testing ML Serving Pipeline API...")

payload = {
    "input_data": [random.random() for _ in range(512)],
    "model_version": "v1",
    "priority": 0
}

req = urllib.request.Request(
    "http://localhost:8000/predict", 
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req) as response:
        resp_data = json.loads(response.read().decode())
        print("✅ Predict Response (Queued):", resp_data)
        
        job_id = resp_data["job_id"]
        print(f"Waiting 1 second for worker to process job {job_id}...")
        time.sleep(1)
        
        req_result = urllib.request.Request(f"http://localhost:8000/result/{job_id}")
        with urllib.request.urlopen(req_result) as res_response:
            print("✅ Result Response:", res_response.read().decode())
except urllib.error.URLError as e:
    print("❌ Connection Error: The API is not available yet. Please ensure 'docker compose up' has finished building and the API logs show it is running.")
except Exception as e:
    print("❌ Error:", e)
