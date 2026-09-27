import sys
from pathlib import Path

# Resolve root and backend directories
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"

# Ensure backend and root are in sys.path
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app import app as application

# Expose WSGI handler for Vercel
app = application
