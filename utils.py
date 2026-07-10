# utils.py
import numpy as np

def convert_numpy(obj):
    """Recursively convert NumPy types to Python native types."""
    if isinstance(obj, (np.int64, np.int32, np.int16)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(item) for item in obj]
    else:
        return obj