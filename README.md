# Local ML Model-Serving Pipeline

A production-grade, containerized ML model-serving pipeline running entirely locally using Minikube and Docker.

## Project Architecture

- **Language:** Python 3.11
- **Inference Framework:** PyTorch
- **API Framework:** FastAPI
- **Container Runtime:** Docker Desktop
- **Orchestration:** Minikube
- **Queue:** Redis
- **Autoscaling:** KEDA + Kubernetes HPA
- **Monitoring:** Prometheus + Grafana

## One-Command Local Setup

1. **Install Prerequisites**: Ensure you have Docker and Python installed.
2. **Generate Dummy Model**: 
   ```bash
   python scripts/generate_dummy_model.py
   ```
3. **Run Dev Environment**:
   ```bash
   docker compose up --build
   ```
   *The API will be available at `http://localhost:8000`.*

## Minikube Deployment

1. **Setup Minikube and K8s Tools**:
   ```bash
   bash scripts/dev-setup.sh
   ```

2. **Build Docker Images into Minikube**:
   ```bash
   eval $(minikube docker-env)
   docker build -f docker/Dockerfile.api -t /ml-api:latest .
   docker build -f docker/Dockerfile.worker -t /ml-worker:latest .
   ```

3. **Deploy Helm Chart**:
   ```bash
   helm upgrade --install ml-serving ./helm/ml-serving \
     --namespace ml-serving --create-namespace \
     --set image.apiRepo=/ml-api \
     --set image.workerRepo=/ml-worker
   ```

4. **Access the Application**:
   ```bash
   kubectl port-forward svc/ml-serving-api 8000:8000 -n ml-serving
   ```

## Load Testing

1. Install Locust:
   ```bash
   pip install locust
   ```
2. Run Load Test:
   ```bash
   locust -f scripts/load_test.py --host http://localhost:8000
   ```
3. Open `http://localhost:8089` to start the Locust UI and simulate traffic. Watch autoscaling via:
   ```bash
   kubectl get hpa -w -n ml-serving
   kubectl get scaledobject -w -n ml-serving
   ```

## Monitoring and Observability

1. Port-forward Grafana:
   ```bash
   kubectl port-forward svc/monitoring-grafana 3000:80 -n monitoring
   ```
2. Open `http://localhost:3000` (Default login: `admin` / `prom-operator`)
