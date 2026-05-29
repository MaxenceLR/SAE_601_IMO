import subprocess
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 1. Chargement de la variable d'environnement
load_dotenv()
dept_cible = os.getenv("DEPARTEMENT_CIBLE", "44")

BASE_DIR = Path(__file__).resolve().parent

print("="*50)
print(f"LANCEMENT DU PIPELINE POUR LE DEPARTEMENT : {dept_cible}")
print("="*50)

scripts = [
    BASE_DIR / "AB_Integration.py",
    BASE_DIR / "BAN_Integration.py",
    BASE_DIR / "DPE_Integration.py",
    BASE_DIR / "DVF_Integration.py",
    BASE_DIR / "PEB_Integration.py"
]

for script in scripts:
    print(f"\nExecution de {script.name} ...")

    # L'environnement actuel (contenant DEPARTEMENT_CIBLE) est automatiquement transmis au subprocess
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True
    )

    print(result.stdout)

    if result.returncode != 0:
        print(f"Erreur critique dans {script.name}")
        print(result.stderr)
        break