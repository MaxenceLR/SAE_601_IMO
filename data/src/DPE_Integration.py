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
        "surface_habitable_immeuble", "type_energie_principale_chauffage",
        "type_energie_principale_ecs"
    ]

    conn = duckdb.connect(str(db_path))

    try:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS raw_dpe (
                {', '.join([col + ' VARCHAR' for col in COLUMNS])}
            )
        """)

        conn.execute(
            "DELETE FROM raw_dpe WHERE code_departement_ban = ?",
            [dept]
        )

        select_param = ",".join(COLUMNS)
        url = (
            f"{BASE_URL}?size={PAGE_SIZE}"
            f"&qs=code_departement_ban%3A{dept}"
            f"&select={select_param}"
        )

        total = 0
        page = 1
        t0 = time.perf_counter()

        while url:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            data = r.json()

            rows = [
                tuple(item.get(col) for col in COLUMNS)
                for item in data.get("results", [])
            ]

            if rows:
                conn.executemany(
                    f"INSERT INTO raw_dpe VALUES ({','.join(['?'] * len(COLUMNS))})",
                    rows
                )
                total += len(rows)
                print(
                    f"   -> Page {page} téléchargée : "
                    f"{total} lignes insérées au total..."
                )

            url = data.get("next")
            page += 1

        print("Ajout de la colonne adresse_normalisee...")

        conn.execute("""
            ALTER TABLE raw_dpe
            ADD COLUMN IF NOT EXISTS adresse_normalisee VARCHAR
        """)

        print("Normalisation des adresses...")

        conn.execute("""
            UPDATE raw_dpe
            SET adresse_normalisee = (
                WITH cleaned AS (
                    SELECT regexp_replace(
                        lower(trim(adresse_ban)),
                        '[àâä]',
                        'a'
                    ) AS s
                ),
                s2 AS (
                    SELECT regexp_replace(s, '[éèêë]', 'e') AS s
                    FROM cleaned
                ),
                s3 AS (
                    SELECT regexp_replace(s, '[îï]', 'i') AS s
                    FROM s2
                ),
                s4 AS (
                    SELECT regexp_replace(s, '[ôö]', 'o') AS s
                    FROM s3
                ),
                s5 AS (
                    SELECT regexp_replace(s, '[ùûü]', 'u') AS s
                    FROM s4
                ),
                s6 AS (
                    SELECT regexp_replace(s, '[ç]', 'c') AS s
                    FROM s5
                ),
                s7 AS (
                    SELECT regexp_replace(s, '\\s+\\d{5}.*$', '') AS s
                    FROM s6
                ),
                s8 AS (
                    SELECT regexp_replace(s, '\\bav\\b', 'avenue') AS s
                    FROM s7
                ),
                s9 AS (
                    SELECT regexp_replace(s, '\\bbd\\b', 'boulevard') AS s
                    FROM s8
                ),
                s10 AS (
                    SELECT regexp_replace(s, '\\bbl\\b', 'boulevard') AS s
                    FROM s9
                ),
                s11 AS (
                    SELECT regexp_replace(s, '\\bche\\b', 'chemin') AS s
                    FROM s10
                ),
                s12 AS (
                    SELECT regexp_replace(s, '\\bcit\\b', 'cite') AS s
                    FROM s11
                ),
                s13 AS (
                    SELECT regexp_replace(s, '\\bimp\\b', 'impasse') AS s
                    FROM s12
                ),
                s14 AS (
                    SELECT regexp_replace(s, '\\bpl\\b', 'place') AS s
                    FROM s13
                ),
                s15 AS (
                    SELECT regexp_replace(s, '\\bpas\\b', 'passage') AS s
                    FROM s14
                ),
                s16 AS (
                    SELECT regexp_replace(s, '\\brte\\b', 'route') AS s
                    FROM s15
                ),
                s17 AS (
                    SELECT regexp_replace(s, '\\brt\\b', 'route') AS s
                    FROM s16
                ),
                s18 AS (
                    SELECT regexp_replace(s, '\\br\\b', 'rue') AS s
                    FROM s17
                ),
                s19 AS (
                    SELECT regexp_replace(s, '\\bvla\\b', 'villa') AS s
                    FROM s18
                ),
                s20 AS (
                    SELECT regexp_replace(s, '[^a-z0-9 ]', ' ') AS s
                    FROM s19
                ),
                s21 AS (
                    SELECT trim(regexp_replace(s, '\\s+', ' ')) AS s
                    FROM s20
                )
                SELECT s FROM s21
            )
            WHERE code_departement_ban = ?
        """, [dept])

        print("\n" + "=" * 50)
        print(f"RAW_DPE TERMINEE POUR LE {dept} !")
        print(f"{total} lignes insérées en {time.perf_counter() - t0:.1f}s")
        print("=" * 50 + "\n")

    finally:
        conn.close()


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    dept = os.getenv("DEPARTEMENT_CIBLE", "44")
    importer_donnees(dept)