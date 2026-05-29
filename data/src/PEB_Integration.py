import duckdb
import requests
import json
import tempfile
import os
import time
from pathlib import Path

def importer_donnees(dept=None):
    print("Démarrage de l'intégration des zones PEB (bruit)...")
    start_time = time.time()

    BASE_DIR = Path(__file__).resolve().parent
    db_path = BASE_DIR / "SAE_601_IMO" / "immo_sae2026.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    PEB_ZONE_URLS = {
        "B": "https://www.data.gouv.fr/api/1/datasets/r/ea77a7b5-0298-49ed-b3ff-caae3b15d022",
        "C": "https://www.data.gouv.fr/api/1/datasets/r/a7f30166-3319-428e-a08e-700e3c0a3755",
        "D": "https://www.data.gouv.fr/api/1/datasets/r/78087339-b725-4825-a9f7-8d4ef92b2963",
    }

    all_features = []

    for zone, url in PEB_ZONE_URLS.items():
        print(f"Téléchargement zone {zone}...")
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        features = data.get("features", [])

        for f in features:
            f.setdefault("properties", {})["peb_zone"] = zone

        all_features.extend(features)

    tmp = tempfile.NamedTemporaryFile(suffix=".geojson", mode="w", delete=False, encoding="utf-8")
    json.dump({"type": "FeatureCollection", "features": all_features}, tmp)
    tmp.close()

    con = duckdb.connect(str(db_path))
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute("DROP TABLE IF EXISTS peb;")

    con.execute(f"""
        CREATE TABLE peb AS
        SELECT * EXCLUDE (geom),
               ST_Transform(geom, 'EPSG:2154', 'EPSG:4326', always_xy := true) AS geom
        FROM ST_Read('{tmp.name.replace(chr(92), '/')}')
    """)

    con.execute("CREATE INDEX idx_peb_geom ON peb USING RTREE (geom);")

    print("\n" + "="*50)
    print("PEB TERMINEE !")
    print(con.execute("SELECT peb_zone, COUNT(*) FROM peb GROUP BY peb_zone ORDER BY peb_zone").fetchall())
    print(f"Temps total de traitement : {round(time.time() - start_time, 2)} secondes.")
    print("="*50 + "\n")

    con.close()
    os.unlink(tmp.name)

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    dept = os.getenv("DEPARTEMENT_CIBLE", "44")
    importer_donnees(dept)