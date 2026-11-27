import sys, os, runpy
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "r5"))
runpy.run_path(os.path.join(here, "r5", "main5.py"), run_name="__main__")
