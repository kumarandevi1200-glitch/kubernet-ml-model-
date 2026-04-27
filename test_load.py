import requests
import concurrent.futures
import time

url = "http://localhost:8000/predict"
payload = {"input_data": [1.0] * 512}

def send_request(i):
    try:
        r = requests.post(url, json=payload, timeout=5)
        return r.status_code
    except Exception as e:
        return str(e)

print("Starting 100 concurrent requests to build up a queue...")
start = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    results = list(executor.map(send_request, range(100)))
end = time.time()

success = results.count(202)
print(f"Sent 100 requests in {end-start:.2f} seconds. Successful (202 Accepted): {success}")
if success < 100:
    print(f"Errors encountered: {[r for r in results if r != 202][:5]}")
