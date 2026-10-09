"""Make the agents importable offline: no API keys, no Pinecone connection."""
import os
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Agents construct an Anthropic client at import time; a placeholder key is enough
# because these tests never make a real call.
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

# tools.pinecone_store connects to Pinecone on import, so replace it with a stub.
_pinecone_stub = types.ModuleType("tools.pinecone_store")
_pinecone_stub.store_discharge_summary = lambda *a, **k: True
_pinecone_stub.store_check_in = lambda *a, **k: True
sys.modules["tools.pinecone_store"] = _pinecone_stub
