import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "r4"))
os.makedirs("out", exist_ok=True)
import runpy; runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "r4", "probe.py"), run_name="__main__")
