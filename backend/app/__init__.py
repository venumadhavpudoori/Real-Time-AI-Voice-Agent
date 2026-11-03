import sys
from pathlib import Path

# Ensure backend directory is in sys.path regardless of execution root
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

"""Real-Time AI Voice Agent Backend Package."""
__version__ = "1.0.0"
