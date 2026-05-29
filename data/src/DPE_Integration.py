import time
import duckdb
import requests

# ==========================================
# CONFIGURATION (Facile à modifier)
# ==========================================
# Change le département ici (ex: "44", "29", "35", etc.)
TARGET_DEPARTMENT = "44"

# Nom du fichier de base de données DuckDB locale
DB_FILE = "dpe_data.duckdb"

# API ADEME - DPE v2 (Logements existants depuis Juillet 2021)
DATASET_ID = "meg-83tjwtg8dyz4vv7h1dqe"
BASE_URL = f"https://data.ademe.fr/data-fair/api/v1/datasets/{DATASET_ID}/lines"
PAGE_SIZE = 10_000

# Colonnes à conserver
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
# FONCTION PRINCIPALE D'INGESTION
# ==========================================
def ingest_dpe_data(dept, db_path):
    select_param = ",".join(COLUMNS)
    
    print(f"Connexion à la base DuckDB : {db_path}")
    # Connexion à DuckDB (crée le fichier s'il n'existe pas)
    conn = duckdb.connect(db_path)
    
    try:
        # 1. Création de la table si elle n'existe pas
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS raw_dpe (
                numero_dpe                      VARCHAR,
                date_etablissement_dpe          DATE,
                date_fin_validite_dpe           DATE,
                type_batiment                   VARCHAR,
                periode_construction            VARCHAR,
                adresse_ban                     VARCHAR,
                adresse_brut                    VARCHAR,
                code_postal_ban                 VARCHAR,
                code_insee_ban                  VARCHAR,
                code_departement_ban            VARCHAR,
                nom_commune_ban                 VARCHAR,
                identifiant_ban                 VARCHAR,
                coordonnee_cartographique_x_ban DOUBLE,
                coordonnee_cartographique_y_ban DOUBLE,
                etiquette_dpe                   VARCHAR,
                etiquette_ges                   VARCHAR,
                conso_5_usages_par_m2_ep        DOUBLE,
                surface_habitable_immeuble      DOUBLE,
                type_energie_principale_chauffage VARCHAR,
                type_energie_principale_ecs     VARCHAR
            )
        """)

        # 2. Nettoyage des anciennes données pour le département choisi
        print(f"Nettoyage des anciennes données pour le département {dept}...")
        conn.execute("DELETE FROM raw_dpe WHERE code_departement_ban = ?", [dept])

        # 3. Pagination et récupération des données via l'API
        url = f"{BASE_URL}?size={PAGE_SIZE}&qs=code_departement_ban%3A{dept}&select={select_param}"
        total_inserted = 0
        page = 0
        t0 = time.perf_counter()

        print(f"Début du téléchargement pour le département {dept}...")
        while url:
            t_page = time.perf_counter()
            response = requests.get(url, timeout=120)
            response.raise_for_status()
            data = response.json()
            t_network = time.perf_counter() - t_page

            rows = [
                tuple(r.get(col) for col in COLUMNS)
                for r in data.get("results", [])
            ]

            if rows:
                t_ins = time.perf_counter()
                # Insertion des lignes par paquets
                conn.executemany(
                    f"INSERT INTO raw_dpe VALUES ({','.join(['?'] * len(COLUMNS))})",
                    rows,
                )
                t_insert = time.perf_counter() - t_ins
                total_inserted += len(rows)
                
                print(
                    f"Dept {dept} — page {page}: {len(rows)} lignes insérées | "
                    f"réseau {t_network:.1f}s | insertion {t_insert:.1f}s | "
                    f"total cumulé {time.perf_counter() - t0:.0f}s"
                )

            url = data.get("next")
            page += 1

        print(f"\n[SUCCÈS] Département {dept} terminé : {total_inserted} lignes insérées au total.")

    finally:
        # Fermeture propre de la connexion
        conn.close()

# Exécution du script
if __name__ == "__main__":
    ingest_dpe_data(TARGET_DEPARTMENT, DB_FILE)