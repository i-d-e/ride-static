import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Make scripts/ importable as top-level modules.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
# Make the src/ package importable as `src.*`.
sys.path.insert(0, str(REPO_ROOT))
