import sys
import time
import shutil
import subprocess
from pathlib import Path

new_exe = Path(sys.argv[1])
target_exe = Path(sys.argv[2])

time.sleep(1)

if target_exe.exists():
    target_exe.unlink()

shutil.move(str(new_exe), str(target_exe))

subprocess.Popen([str(target_exe)])
