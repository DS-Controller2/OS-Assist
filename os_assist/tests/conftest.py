import sys
import os
from pathlib import Path

# Add the project root (os_assist) to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
