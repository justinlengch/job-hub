import sys, os
# insert the backend root so `import app...` works
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))