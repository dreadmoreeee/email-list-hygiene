import sys
from pathlib import Path

TOOL_DIR = str(Path(__file__).resolve().parent.parent)
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)
