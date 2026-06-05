import subprocess
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 1. Chargement de la variable d'environnement
load_dotenv()
dept_cible = os.getenv("DEPARTEMENT_CIBLE", "44")

# Définition des chemins
BASE_DIR = Path(__file__).resolve().parent
# On remonte d'un dossier (data) puis on va dans app/app.py
APP_PATH = BASE_DIR.parent / "app" / "app.py" 

print("="*50)
print(f"LANCEMENT DU PIPELINE POUR LE DEPARTEMENT : {dept_cible}")
print("="*50)

scripts = [
    #BASE_DIR / "AB_Integration.py",
    #BASE_DIR / "BAN_Integration.py",
    #BASE_DIR / "DPE_Integration.py",
    #BASE_DIR / "DVF_Integration.py",
    #BASE_DIR / "PEB_Integration.py",
    #BASE_DIR / "Optimisation_Integration.py"
]

# Variable pour suivre si tout s'est bien passé
pipeline_reussi = True

for script in scripts:
    print(f"\nExecution de {script.name} ...")

    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True
    )

    print(result.stdout)

    if result.returncode != 0:
        print(f"Erreur critique dans {script.name}")
        print(result.stderr)
        pipeline_reussi = False
        break # On arrête tout en cas d'erreur

# --- NOUVEAUTÉ : Lancement de l'application Streamlit ---
if pipeline_reussi:
    print("\n" + "="*50)
    print("BASE DE DONNÉES PRÊTE !")
    print("Démarrage du serveur Streamlit...")
    print("(Faites Ctrl+C dans ce terminal pour arrêter l'application)")
    print("="*50 + "\n")
    
    try:
        # Équivaut à taper : python -m streamlit run .../app.py
        subprocess.run([sys.executable, "-m", "streamlit", "run", str(APP_PATH)])
    except KeyboardInterrupt:
        print("\nArrêt du serveur Streamlit. À bientôt !")