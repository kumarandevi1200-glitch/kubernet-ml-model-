from prometheus_client import Counter, Histogram, Gauge

request_total = Counter(
    "request_total", "Total requests", ["endpoint", "status_code"]
)
request_duration_seconds = Histogram(
    "request_duration_seconds", "Request duration", ["endpoint"]
)
queue_depth = Gauge("queue_depth", "Depth of the Redis queue")
inference_duration_seconds = Histogram(
    "inference_duration_seconds", "Inference duration", ["model_version"]
)
queue_wait_seconds = Histogram(
    "queue_wait_seconds", "Time spent in queue"
)
cold_start_total = Counter("cold_start_total", "Number of cold starts")
