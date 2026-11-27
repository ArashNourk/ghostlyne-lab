import sys, os, runpy
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "r4"))
runpy.run_path(os.path.join(here, "r4", "mon_run.py"), run_name="__main__")
