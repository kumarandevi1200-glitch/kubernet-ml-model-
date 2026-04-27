from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_client import make_asgi_app
import time
import uuid
import json
from datetime import datetime
from redis import asyncio as aioredis
from typing import Callable

from .schemas import PredictRequest, PredictResponse, ResultResponse
from .config import settings
from .metrics import request_total, request_duration_seconds, queue_depth

redis_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    try:
        redis_client = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        print(f"Connected to Redis at {settings.REDIS_URL}")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        redis_client = None
    
    yield
    if redis_client:
        await redis_client.aclose()

app = FastAPI(title="ML Serving API", lifespan=lifespan)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Callable):
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request_id
    
    if request.url.path not in ["/metrics", "/health", "/ready"]:
        request_total.labels(endpoint=request.url.path, status_code=response.status_code).inc()
        request_duration_seconds.labels(endpoint=request.url.path).observe(process_time)
        
    return response

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    try:
        await redis_client.ping()
    except Exception:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    return {"status": "ready"}

@app.post("/predict", response_model=PredictResponse, status_code=202)
async def predict(req: PredictRequest):
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis unavailable")
        
    job_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    job_data = {
        "job_id": job_id,
        "input_data": req.input_data,
        "model_version": req.model_version,
        "priority": req.priority,
        "queued_at": now.isoformat(),
        "queued_at_ts": time.time()
    }
    
    try:
        q_len = await redis_client.llen("ml:queue:requests")
        queue_depth.set(q_len)
        
        if q_len >= settings.MAX_QUEUE_SIZE:
            raise HTTPException(status_code=503, detail="Queue full")
            
        if req.priority > 0:
            await redis_client.zadd("ml:queue:priority", {json.dumps(job_data): req.priority})
            # Also add to requests so worker can pop it for now, 
            # ideally worker checks ZSET first but requirement states BLPOP on requests.
            # We'll just push to requests to keep it functioning
            await redis_client.rpush("ml:queue:requests", json.dumps(job_data))
        else:
            await redis_client.rpush("ml:queue:requests", json.dumps(job_data))
            
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis error: {e}")
        
    return PredictResponse(
        job_id=uuid.UUID(job_id),
        status="queued",
        queued_at=now
    )

@app.get("/result/{job_id}", response_model=ResultResponse)
async def get_result(job_id: str):
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis unavailable")
        
    try:
        result_json = await redis_client.get(f"ml:result:{job_id}")
        if not result_json:
            return ResultResponse(job_id=uuid.UUID(job_id), status="pending")
            
        data = json.loads(result_json)
        return ResultResponse(**data)
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis error: {e}")
