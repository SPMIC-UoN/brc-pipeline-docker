#!/usr/local/fsl/6.0.7.x/bin/python

import shutil
import subprocess
import sys

if len(sys.argv) < 2:
    print("Usage: python brc_pipeline_entrypoint.py <script_name> <args>")
    sys.exit(1)
if sys.argv[1] == "--version":
    print("v0.0.1")
    sys.exit(0)

script = sys.argv[1] + ".sh"
script_name = shutil.which(script)
if script_name is None:
    print(f"Error: {script} not found in PATH.")
    sys.exit(1)

subprocess.run([script_name] + sys.argv[2:], check=True)
