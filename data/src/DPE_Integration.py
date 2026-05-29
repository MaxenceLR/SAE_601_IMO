import time
import duckdb
import requests
from pathlib import Path

def importer_donnees(dept):
    print(f"Démarrage de l'intégration DPE pour le département {dept}...")

    BASE_DIR = Path(__file__).resolve().parent
    db_path = BASE_DIR / "SAE_601_IMO" / "immo_sae2026.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    DATASET_ID = "meg-83tjwtg8dyz4vv7h1dqe"
    BASE_URL = f"https://data.ademe.fr/data-fair/api/v1/datasets/{DATASET_ID}/lines"
    PAGE_SIZE = 10_000

    COLUMNS = [
        "numero_dpe", "date_etablissement_dpe", "date_fin_validite_dpe", "type_batiment",
        "periode_construction", "adresse_ban", "adresse_brut", "code_postal_ban",
        "code_insee_ban", "code_departement_ban", "nom_commune_ban", "identifiant_ban",
        "coordonnee_cartographique_x_ban", "coordonnee_cartographique_y_ban",
        "etiquette_dpe", "etiquette_ges", "conso_5_usages_par_m2_ep",
        "surface_habitable_immeuble", "type_energie_principale_chauffage", "type_energie_principale_ecs"
    ]

    conn = duckdb.connect(str(db_path))

    try:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS raw_dpe (
                {', '.join([col + ' VARCHAR' for col in COLUMNS])}
            )
        """)

        conn.execute("DELETE FROM raw_dpe WHERE code_departement_ban = ?", [dept])

        select_param = ",".join(COLUMNS)
        url = f"{BASE_URL}?size={PAGE_SIZE}&qs=code_departement_ban%3A{dept}&select={select_param}"

        total = 0
        page = 1
        t0 = time.perf_counter()

        while url:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            data = r.json()

            rows = [tuple(item.get(col) for col in COLUMNS) for item in data.get("results", [])]

            if rows:
                conn.executemany(f"INSERT INTO raw_dpe VALUES ({','.join(['?'] * len(COLUMNS))})", rows)
                total += len(rows)
                print(f"   -> Page {page} téléchargée : {total} lignes insérées au total...")

            url = data.get("next")
            page += 1

        print("\n" + "="*50)
        print(f"RAW_DPE TERMINEE POUR LE {dept} !")
        print(f"{total} lignes insérées en {time.perf_counter() - t0:.1f}s")
        print("="*50 + "\n")

    finally:
        conn.close()

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    dept = os.getenv("DEPARTEMENT_CIBLE", "44")
    importer_donnees(dept)