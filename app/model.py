import torch
import threading
import logging
from typing import List
from multiprocessing import shared_memory
import io
import time
from .config import settings

logger = logging.getLogger("ml_serving")

class ModelLoader:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelLoader, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance

    def _initialize(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        start_time = time.time()
        
        from .metrics import cold_start_total
        cold_start_total.inc()

        model_bytes = None
        shm = None
        try:
            # Try to attach to shared memory
            shm = shared_memory.SharedMemory(name=settings.SHARED_MEMORY_NAME, create=False)
            logger.info(f"Attached to shared memory: {settings.SHARED_MEMORY_NAME}")
            buffer = bytes(shm.buf)
            # Remove trailing null bytes if preload_weights pads it, but usually not needed
            model_bytes = io.BytesIO(buffer)
        except Exception as e:
            logger.warning(f"Failed to attach to shared memory, falling back to disk: {e}")
            with open(settings.MODEL_PATH, "rb") as f:
                model_bytes = io.BytesIO(f.read())

        # Support both TorchScript and state_dict
        try:
            self.model = torch.jit.load(model_bytes, map_location=self.device)
        except Exception:
            model_bytes.seek(0)
            self.model = torch.load(model_bytes, map_location=self.device)
            self.model.eval()
            
        if shm:
            shm.close()

        weight_size_mb = model_bytes.getbuffer().nbytes / (1024 * 1024)
        load_time = time.time() - start_time
        logger.info(f"Model loaded in {load_time:.2f}s on {self.device}. Size: {weight_size_mb:.2f} MB")

        # Warm-up
        logger.info("Starting model warm-up")
        dummy_input = torch.randn(3, 512, device=self.device)
        with torch.no_grad():
            for _ in range(3):
                if self.device.type == "cuda":
                    with torch.cuda.amp.autocast():
                        self.model(dummy_input)
                else:
                    self.model(dummy_input)
        logger.info("Model warm-up complete")

    def infer(self, batch: List[List[float]]) -> List[List[float]]:
        tensor_batch = torch.tensor(batch, dtype=torch.float32)
        
        if self.device.type == "cuda":
            tensor_batch = tensor_batch.pin_memory()
            stream = torch.cuda.Stream()
            with torch.cuda.stream(stream):
                tensor_batch = tensor_batch.to(self.device, non_blocking=True)
                with torch.no_grad(), torch.cuda.amp.autocast():
                    output = self.model(tensor_batch)
            torch.cuda.current_stream().wait_stream(stream)
        else:
            with torch.no_grad():
                output = self.model(tensor_batch)
                
        return output.cpu().tolist()
