import requests
import duckdb
import time
from pathlib import Path

def importer_donnees(dept):
    print(f"Démarrage de l'intégration DVF pour le département {dept}...")
    start_time = time.time()

    BASE_DIR = Path(__file__).resolve().parent
    base_path = BASE_DIR / "SAE_601_IMO"
    file_path = base_path / "dvf.csv.gz"
    db_path = base_path / "immo_sae2026.db"
    base_path.mkdir(exist_ok=True)

    url = "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres-geolocalisees/20260424-090024/dvf.csv.gz"

    if not file_path.exists():
        print("Téléchargement du fichier national DVF en cours...")
        response = requests.get(url, stream=True)
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print("Téléchargement terminé.")
    else:
        print("Fichier national DVF déjà présent.")

    con = duckdb.connect(str(db_path))
    con.execute("INSTALL spatial; LOAD spatial;")

    con.execute("DROP TABLE IF EXISTS dvf;")

    print(f"Import DVF filtré sur le département {dept}...")
    
    con.execute(f"""
        CREATE TABLE dvf AS
        SELECT *,
               ST_Point(CAST(longitude AS DOUBLE), CAST(latitude AS DOUBLE)) AS geom
        FROM read_csv_auto('{str(file_path).replace(chr(92), '/')}', all_varchar=true, ignore_errors=true)
        WHERE latitude IS NOT NULL
        AND longitude IS NOT NULL
        AND code_departement = '{dept}'
    """)

    nb_lignes = con.execute("SELECT COUNT(*) FROM dvf").fetchone()[0]
    
    print("\n" + "="*50)
    print(f"DVF TERMINEE POUR LE {dept} !")
    print(f"Nombre de ventes extraites : {nb_lignes}")
    print(f"Temps total de traitement : {round(time.time() - start_time, 2)} secondes.")
    print("="*50 + "\n")
    
    con.close()

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    dept = os.getenv("DEPARTEMENT_CIBLE", "44")
    importer_donnees(dept)