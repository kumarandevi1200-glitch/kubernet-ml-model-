#!/bin/bash
set -e

echo "Starting preload_weights.sh"

MODEL_PATH=${MODEL_PATH:-"/app/weights/model.pt"}
SHARED_MEMORY_NAME=${SHARED_MEMORY_NAME:-"ml_model_weights"}

if [ ! -f "$MODEL_PATH" ]; then
    echo "Warning: Model file not found at $MODEL_PATH. Ensure it is mounted correctly."
    exit 0
fi

python3 -c "
import os
import sys
from multiprocessing import shared_memory

model_path = '$MODEL_PATH'
shm_name = '$SHARED_MEMORY_NAME'

try:
    file_size = os.path.getsize(model_path)
    
    try:
        existing_shm = shared_memory.SharedMemory(name=shm_name)
        existing_shm.unlink()
    except FileNotFoundError:
        pass

    shm = shared_memory.SharedMemory(name=shm_name, create=True, size=file_size)
    
    with open(model_path, 'rb') as f:
        shm.buf[:file_size] = f.read()
        
    print(f'Successfully loaded {file_size} bytes into shared memory {shm_name}')
    
    from multiprocessing.resource_tracker import unregister
    unregister(shm._name, 'shared_memory')
except Exception as e:
    print(f'Error preloading weights: {e}')
    sys.exit(1)
"

echo "Preload complete."
