from locust import HttpUser, task, between
import random
import time

class MLUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(9)
    def predict(self):
        input_data = [random.random() for _ in range(512)]
        payload = {
            "input_data": input_data,
            "model_version": "v1",
            "priority": random.randint(0, 5)
        }
        
        with self.client.post("/predict", json=payload, catch_response=True) as response:
            if response.status_code == 202:
                job_id = response.json()["job_id"]
                time.sleep(1)
                self.client.get(f"/result/{job_id}", name="/result")
            else:
                response.failure(f"Failed with {response.status_code}")

    @task(1)
    def check_health(self):
        self.client.get("/health")
