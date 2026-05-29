import time
import duckdb
import requests
from pathlib import Path

# ==========================================
# CONFIGURATION
# ==========================================

TARGET_DEPARTMENT = "44"

# Dossier projet portable (comme DVF)
base_path = Path(__file__).resolve().parent / "SAE_601_IMO"
db_path = base_path / "immo_sae2026.db"

base_path.mkdir(exist_ok=True)

print("Dossier data :", base_path)
print("Base DPE :", db_path)

# ==========================================
# API ADEME
# ==========================================

DATASET_ID = "meg-83tjwtg8dyz4vv7h1dqe"
BASE_URL = f"https://data.ademe.fr/data-fair/api/v1/datasets/{DATASET_ID}/lines"
PAGE_SIZE = 10_000

COLUMNS = [
    "numero_dpe",
    "date_etablissement_dpe",
    "date_fin_validite_dpe",
    "type_batiment",
    "periode_construction",
    "adresse_ban",
    "adresse_brut",
    "code_postal_ban",
    "code_insee_ban",
    "code_departement_ban",
    "nom_commune_ban",
    "identifiant_ban",
    "coordonnee_cartographique_x_ban",
    "coordonnee_cartographique_y_ban",
    "etiquette_dpe",
    "etiquette_ges",
    "conso_5_usages_par_m2_ep",
    "surface_habitable_immeuble",
    "type_energie_principale_chauffage",
    "type_energie_principale_ecs",
]

# ==========================================
# INGESTION
# ==========================================

def ingest_dpe_data(dept, db_file):

    select_param = ",".join(COLUMNS)

    print(f"Connexion DuckDB : {db_file}")
    conn = duckdb.connect(str(db_file))

    try:
        # Table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_dpe (
                numero_dpe VARCHAR,
                date_etablissement_dpe DATE,
                date_fin_validite_dpe DATE,
                type_batiment VARCHAR,
                periode_construction VARCHAR,
                adresse_ban VARCHAR,
                adresse_brut VARCHAR,
                code_postal_ban VARCHAR,
                code_insee_ban VARCHAR,
                code_departement_ban VARCHAR,
                nom_commune_ban VARCHAR,
                identifiant_ban VARCHAR,
                coordonnee_cartographique_x_ban DOUBLE,
                coordonnee_cartographique_y_ban DOUBLE,
                etiquette_dpe VARCHAR,
                etiquette_ges VARCHAR,
                conso_5_usages_par_m2_ep DOUBLE,
                surface_habitable_immeuble DOUBLE,
                type_energie_principale_chauffage VARCHAR,
                type_energie_principale_ecs VARCHAR
            )
        """)

        # Nettoyage département
        print(f"Nettoyage département {dept}...")
        conn.execute("DELETE FROM raw_dpe WHERE code_departement_ban = ?", [dept])

        # API
        url = f"{BASE_URL}?size={PAGE_SIZE}&qs=code_departement_ban%3A{dept}&select={select_param}"

        total = 0
        page = 0
        t0 = time.perf_counter()

        print(f"Début ingestion DPE dept {dept}")

        while url:
            t_page = time.perf_counter()

            r = requests.get(url, timeout=120)
            r.raise_for_status()
            data = r.json()

            t_network = time.perf_counter() - t_page

            rows = [
                tuple(item.get(col) for col in COLUMNS)
                for item in data.get("results", [])
            ]

            if rows:
                t_ins = time.perf_counter()

                conn.executemany(
                    f"INSERT INTO raw_dpe VALUES ({','.join(['?'] * len(COLUMNS))})",
                    rows,
                )

                t_insert = time.perf_counter() - t_ins

                total += len(rows)

                print(
                    f"Dept {dept} | page {page} | "
                    f"{len(rows)} lignes | réseau {t_network:.1f}s | "
                    f"insert {t_insert:.1f}s | total {total}"
                )

            url = data.get("next")
            page += 1

        print(f"\n TERMINE : {total} lignes insérées pour le département {dept}")
        print(f"Temps total : {time.perf_counter() - t0:.1f}s")

    finally:
        conn.close()


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":
    ingest_dpe_data(TARGET_DEPARTMENT, db_path)