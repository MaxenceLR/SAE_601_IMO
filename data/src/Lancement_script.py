import subprocess
import sys
from pathlib import Path
import subprocess
import sys

BASE_DIR = Path(__file__).resolve().parent  # dossier du launcher

scripts = [
    BASE_DIR / "AB_Integration.py",
    BASE_DIR / "BAN_Integration.py",
    BASE_DIR / "DPE_Integration.py",
    BASE_DIR / "DVF_Integration.py",
    BASE_DIR / "PEB_Integration.py"
]

for script in scripts:
    print(f"Lancement de {script} ...")

    result = subprocess.run(
        [sys.executable, script],
        capture_output=True,
        text=True
    )

    print(result.stdout)

    if result.returncode != 0:
        print(f"Erreur dans {script}")
        print(result.stderr)
        break