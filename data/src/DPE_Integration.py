import requests
import pandas as pd
import duckdb

# =========================
# 1. CONFIG API
# =========================

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

# =========================
# 2. EXTRACTION (FILTRÉ 44)
# =========================

all_rows = []
offset = 0

while True:

    params = {
        "size": PAGE_SIZE,
        "offset": offset,
        "q": "code_departement_ban:44"
    }

    response = requests.get(BASE_URL, params=params)

    if response.status_code != 200:
        print(response.text)
        response.raise_for_status()

    rows = response.json().get("results", [])

    if not rows:
        break

    filtered_rows = [
        {col: row.get(col) for col in COLUMNS}
        for row in rows
    ]

    all_rows.extend(filtered_rows)

    print(f"Offset {offset} → {len(filtered_rows)} lignes (44 uniquement)")

    if len(rows) < PAGE_SIZE:
        break

    offset += PAGE_SIZE

# =========================
# 3. DATAFRAME
# =========================

df = pd.DataFrame(all_rows, columns=COLUMNS)

df["date_etablissement_dpe"] = pd.to_datetime(df["date_etablissement_dpe"], errors="coerce")
df["date_fin_validite_dpe"] = pd.to_datetime(df["date_fin_validite_dpe"], errors="coerce")

for col in [
    "coordonnee_cartographique_x_ban",
    "coordonnee_cartographique_y_ban",
    "conso_5_usages_par_m2_ep",
    "surface_habitable_immeuble"
]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

print("DataFrame 44 :", df.shape)

# =========================
# 4. DUCKDB
# =========================

con = duckdb.connect("DPE.db")

con.execute("""
CREATE TABLE IF NOT EXISTS raw_dpe (
    numero_dpe                         VARCHAR,
    date_etablissement_dpe             DATE,
    date_fin_validite_dpe              DATE,
    type_batiment                      VARCHAR,
    periode_construction               VARCHAR,
    adresse_ban                        VARCHAR,
    adresse_brut                       VARCHAR,
    code_postal_ban                    VARCHAR,
    code_insee_ban                     VARCHAR,
    code_departement_ban               VARCHAR,
    nom_commune_ban                    VARCHAR,
    identifiant_ban                    VARCHAR,
    coordonnee_cartographique_x_ban    DOUBLE,
    coordonnee_cartographique_y_ban    DOUBLE,
    etiquette_dpe                      VARCHAR,
    etiquette_ges                      VARCHAR,
    conso_5_usages_par_m2_ep           DOUBLE,
    surface_habitable_immeuble         DOUBLE,
    type_energie_principale_chauffage  VARCHAR,
    type_energie_principale_ecs        VARCHAR
)
""")

con.register("df_temp", df)

con.execute("""
INSERT INTO raw_dpe
SELECT * FROM df_temp
""")

print("✔ Données DPE intégrées")

print(con.execute("SELECT COUNT(*) FROM raw_dpe").fetchone())

con.close()