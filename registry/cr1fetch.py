import sys, os, runpy
here = os.path.dirname(os.path.abspath(__file__))
runpy.run_path(os.path.join(here, "cr1", "fetch_cr.py"), run_name="__main__")
