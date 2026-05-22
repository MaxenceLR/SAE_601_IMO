import requests
import pandas as pd
import duckdb
import json
# =========================
# 1. CHARGEMENT GEOJSON
# =========================

url = "https://static.data.gouv.fr/resources/zonage-des-plan-dexposition-au-bruit-peb/20200602-202334/c-dgac-peb-metro-za.geojson"

data = requests.get(url).json()

df = pd.DataFrame([
    {
        "ZONE": f["properties"].get("ZONE"),
        "CODE_OACI": f["properties"].get("CODE_OACI"),
        "NOM": f["properties"].get("NOM"),
        "PRODUCTEUR": f["properties"].get("PRODUCTEUR"),
        "REF_DOC": f["properties"].get("REF_DOC"),
        "INDLDENEXT": f["properties"].get("INDLDENEXT"),
        "INDLDENINT": f["properties"].get("INDLDENINT"),
        "DATE_ARRET": f["properties"].get("DATE_ARRET"),
        "DATE_MAJ": f["properties"].get("DATE_MAJ"),
        "ID_MAP": f["properties"].get("ID_MAP"),
        "geometry": json.dumps(f["geometry"])   # 👈 IMPORTANT
    }
    for f in data["features"]
])

print("Données chargées :", df.shape)

# =========================
# 2. BASE DUCKDB
# =========================

con = duckdb.connect(r"C:/temp/dvf.db")
con.execute("DROP TABLE IF EXISTS peb")
con.execute("""
CREATE TABLE IF NOT EXISTS peb (
    zone VARCHAR,
    code_oaci VARCHAR,
    nom VARCHAR,
    producteur VARCHAR,
    ref_doc VARCHAR,
    indldenext VARCHAR,
    indldenint VARCHAR,
    date_arret VARCHAR,
    date_maj VARCHAR,
    id_map VARCHAR,
    geometry VARCHAR
)
""")

# =========================
# 3. INSERTION
# =========================

con.register("df_temp", df)

con.execute("""
INSERT INTO peb
SELECT
    ZONE,
    CODE_OACI,
    NOM,
    PRODUCTEUR,
    REF_DOC,
    INDLDENEXT,
    INDLDENINT,
    DATE_ARRET,
    DATE_MAJ,
    ID_MAP,
    geometry
FROM df_temp
""")

print("Table PEB intégrée ✔")

