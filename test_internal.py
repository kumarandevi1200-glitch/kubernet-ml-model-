import urllib.request
import json
import concurrent.futures

url = "http://localhost:8000/predict"
data = json.dumps({"input_data": [1.0] * 512}).encode("utf-8")
headers = {"Content-Type": "application/json"}

def send_request(_):
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status
    except Exception as e:
        return str(e)

print("Starting internal load test...")
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    results = list(executor.map(send_request, range(100)))

success = results.count(202)
print(f"Successful (202 Accepted): {success}")
if success < 100:
    print(f"Errors: {[r for r in results if r != 202][:5]}")
