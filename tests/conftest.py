import os
import sys

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

ANALYTICS_DIR = os.path.join(PROJECT_ROOT, "analytics")

if ANALYTICS_DIR not in sys.path:
    sys.path.insert(0, ANALYTICS_DIR)
