import sys, os, runpy
here = os.path.dirname(os.path.abspath(__file__))
runpy.run_path(os.path.join(here, "daily1", "daily1.py"), run_name="__main__")
