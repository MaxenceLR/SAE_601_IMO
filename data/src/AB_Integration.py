import duckdb
import urllib.request
import os
from pathlib import Path

def importer_donnees(dept=None):
    print("Démarrage de l'intégration des frontières administratives (Admin Express)...")

    # Standardisation du chemin de la base
    BASE_DIR = Path(__file__).resolve().parent
    db_path = BASE_DIR / "SAE_601_IMO" / "immo_sae2026.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    data_dir = BASE_DIR / "data"
    data_dir.mkdir(exist_ok=True)

    url_admin = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/communes-version-simplifiee.geojson"
    fichier_local = data_dir / "limites_administratives.geojson"

    if fichier_local.exists():
        try:
            import json
            with open(fichier_local, 'r', encoding='utf-8') as f:
                json.load(f)
        except Exception:
            print("Fichier corrompu détecté. Suppression en cours...")
            os.remove(fichier_local)

    if not fichier_local.exists():
        print("Téléchargement des polygones géographiques...")
        urllib.request.urlretrieve(url_admin, fichier_local)
        print("Téléchargement terminé !")
    else:
        print("Le fichier spatial est déjà présent en local.")

    con = duckdb.connect(str(db_path))
    con.execute("INSTALL spatial; LOAD spatial;")
    
    con.execute("DROP TABLE IF EXISTS dim_geographie;")

    con.execute(f"""
        CREATE TABLE dim_geographie AS 
        SELECT * FROM st_read('{str(fichier_local).replace(chr(92), '/')}');
    """)

    nb_polygones = con.execute("SELECT COUNT(*) FROM dim_geographie").fetchone()[0]

    print("\n" + "="*50)
    print("DIM_GEOGRAPHIE TERMINEE !")
    print(f"{nb_polygones:,.0f} entités géographiques ont été chargées avec succès.")
    print("="*50 + "\n")
    con.close()

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    dept = os.getenv("DEPARTEMENT_CIBLE", "44")
    importer_donnees(dept)