import asyncio
import json
import logging
import time
from redis import asyncio as aioredis
from .config import settings
from .model import ModelLoader
from .metrics import queue_wait_seconds, inference_duration_seconds

logging.basicConfig(level=settings.LOG_LEVEL.upper())
logger = logging.getLogger("queue_worker")

async def worker_loop():
    redis = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    model = ModelLoader()
    
    batch_size = 8
    batch_window_ms = 20
    
    logger.info("Worker started, waiting for jobs...")
    while True:
        jobs = []
        start_wait = time.time()
        
        try:
            result = await redis.blpop("ml:queue:requests", timeout=5)
        except Exception as e:
            logger.error(f"Redis error: {e}")
            await asyncio.sleep(1)
            continue
            
        if not result:
            continue
            
        _, job_json = result
        jobs.append(json.loads(job_json))
        
        end_time = time.time() + (batch_window_ms / 1000.0)
        while len(jobs) < batch_size and time.time() < end_time:
            job_json = await redis.lpop("ml:queue:requests")
            if job_json:
                jobs.append(json.loads(job_json))
            else:
                await asyncio.sleep(0.001)
                
        wait_time = time.time() - start_wait
        queue_wait_seconds.observe(wait_time)
        
        try:
            inputs = [job["input_data"] for job in jobs]
            
            inf_start = time.time()
            outputs = model.infer(inputs)
            inf_duration = time.time() - inf_start
            
            inference_duration_seconds.labels(model_version=settings.MODEL_VERSION).observe(inf_duration)
            
            pipeline = redis.pipeline()
            for i, job in enumerate(jobs):
                job_id = job["job_id"]
                result_data = {
                    "job_id": job_id,
                    "status": "done",
                    "result": outputs[i],
                    "latency_ms": (time.time() - job["queued_at_ts"]) * 1000
                }
                pipeline.setex(f"ml:result:{job_id}", 300, json.dumps(result_data))
            await pipeline.execute()
            
        except Exception as e:
            logger.error(f"Batch inference failed: {e}")
            for job in jobs:
                job_id = job["job_id"]
                retry_key = f"ml:retry:{job_id}"
                retries = await redis.incr(retry_key)
                if retries == 1:
                    await redis.expire(retry_key, 60)
                    
                if retries >= 3:
                    await redis.rpush("ml:queue:dead", json.dumps(job))
                    error_data = {"job_id": job_id, "status": "failed"}
                    await redis.setex(f"ml:result:{job_id}", 300, json.dumps(error_data))
                else:
                    await asyncio.sleep(2 ** (retries - 1))
                    await redis.rpush("ml:queue:requests", json.dumps(job))

if __name__ == "__main__":
    asyncio.run(worker_loop())
