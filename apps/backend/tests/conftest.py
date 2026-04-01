import os
import sys

# Provide deterministic defaults so backend modules that initialize services at
# import time can load inside tests without real cloud credentials.
os.environ.setdefault("SUPABASE_URL", "http://test.supabase.local")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")

# insert the backend root so `import app...` works
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
