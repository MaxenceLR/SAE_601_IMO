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

    # =========================
    # NORMALISATION ADRESSE
    # =========================

    print("Ajout colonne adresse_normalisee...")

    con.execute("""
        ALTER TABLE dvf
        ADD COLUMN IF NOT EXISTS adresse_normalisee VARCHAR
    """)

    print("Normalisation des adresses DVF...")

    con.execute("""
        UPDATE dvf
        SET adresse_normalisee = (
            WITH cleaned AS (
                SELECT lower(trim(
                    COALESCE(CAST(adresse_numero AS VARCHAR), '') || ' ' ||
                    COALESCE(adresse_suffixe, '') || ' ' ||
                    COALESCE(adresse_nom_voie, '')
                )) AS s
            ),
            s2  AS (SELECT regexp_replace(s, '[àâä]', 'a') AS s FROM cleaned),
            s3  AS (SELECT regexp_replace(s, '[éèêë]', 'e') AS s FROM s2),
            s4  AS (SELECT regexp_replace(s, '[îï]', 'i') AS s FROM s3),
            s5  AS (SELECT regexp_replace(s, '[ôö]', 'o') AS s FROM s4),
            s6  AS (SELECT regexp_replace(s, '[ùûü]', 'u') AS s FROM s5),
            s7  AS (SELECT regexp_replace(s, '[ç]', 'c') AS s FROM s6),

            s8  AS (SELECT regexp_replace(s, '\\bav\\b',  'avenue')    AS s FROM s7),
            s9  AS (SELECT regexp_replace(s, '\\bbd\\b',  'boulevard') AS s FROM s8),
            s10 AS (SELECT regexp_replace(s, '\\bbl\\b',  'boulevard') AS s FROM s9),
            s11 AS (SELECT regexp_replace(s, '\\bche\\b', 'chemin')    AS s FROM s10),
            s12 AS (SELECT regexp_replace(s, '\\bcit\\b', 'cite')      AS s FROM s11),
            s13 AS (SELECT regexp_replace(s, '\\bimp\\b', 'impasse')   AS s FROM s12),
            s14 AS (SELECT regexp_replace(s, '\\bpl\\b',  'place')     AS s FROM s13),
            s15 AS (SELECT regexp_replace(s, '\\bpas\\b', 'passage')   AS s FROM s14),
            s16 AS (SELECT regexp_replace(s, '\\brte\\b', 'route')     AS s FROM s15),
            s17 AS (SELECT regexp_replace(s, '\\brt\\b',  'route')     AS s FROM s16),
            s18 AS (SELECT regexp_replace(s, '\\br\\b',   'rue')       AS s FROM s17),
            s19 AS (SELECT regexp_replace(s, '\\bvla\\b', 'villa')     AS s FROM s18),

            s20 AS (SELECT regexp_replace(s, '[^a-z0-9 ]', ' ') AS s FROM s19),
            s21 AS (SELECT trim(regexp_replace(s, '\\s+', ' ')) AS s FROM s20)

            SELECT s FROM s21
        )
        WHERE code_departement = ?
    """, [dept])

    print("\n" + "=" * 50)
    print(f"DVF TERMINEE POUR LE {dept} !")
    print(f"Nombre de ventes extraites : {nb_lignes}")
    print(f"Temps total de traitement : {round(time.time() - start_time, 2)} secondes.")
    print("=" * 50 + "\n")

    con.close()


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    dept = os.getenv("DEPARTEMENT_CIBLE", "44")
    importer_donnees(dept)