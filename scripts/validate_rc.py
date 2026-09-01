import subprocess
import sys

checks = [
    ("ruff", ["ruff","check","."]),
    ("mypy", ["mypy","app"]),
    ("pytest", ["pytest","-q"]),
]
failed=[]
for name,cmd in checks:
    print(f"== {name} ==")
    result=subprocess.run(cmd,check=False)
    if result.returncode:
        failed.append(name)
if failed:
    print("FAILED:", ", ".join(failed))
    sys.exit(1)
print("RC static/test validation passed.")
