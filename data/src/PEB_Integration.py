import duckdb
import requests
import json
import tempfile
import os

# =========================
# CONFIG
# =========================

db_path = r"C:/temp/dvf.db"

PEB_ZONE_URLS = {
    "B": "https://www.data.gouv.fr/api/1/datasets/r/ea77a7b5-0298-49ed-b3ff-caae3b15d022",
    "C": "https://www.data.gouv.fr/api/1/datasets/r/a7f30166-3319-428e-a08e-700e3c0a3755",
    "D": "https://www.data.gouv.fr/api/1/datasets/r/78087339-b725-4825-a9f7-8d4ef92b2963",
}

# =========================
# DOWNLOAD GEOJSON
# =========================

all_features = []

for zone, url in PEB_ZONE_URLS.items():

    print(f"Téléchargement zone {zone}...")

    response = requests.get(url)
    data = response.json()

    features = data.get("features", [])

    # ajout zone
    for f in features:
        f.setdefault("properties", {})["peb_zone"] = zone

    all_features.extend(features)

    print(f"{len(features)} polygones")

# =========================
# TEMP FILE
# =========================

tmp = tempfile.NamedTemporaryFile(
    suffix=".geojson",
    mode="w",
    delete=False,
    encoding="utf-8"
)

json.dump(
    {
        "type": "FeatureCollection",
        "features": all_features
    },
    tmp
)

tmp.close()

# =========================
# DUCKDB
# =========================

con = duckdb.connect(db_path)

con.execute("INSTALL spatial")
con.execute("LOAD spatial")

con.execute("DROP TABLE IF EXISTS peb")

# =========================
# IMPORT SPATIAL
# =========================

con.execute(f"""
CREATE TABLE peb AS
SELECT
    * EXCLUDE (geom),

    ST_Transform(
        geom,
        'EPSG:2154',
        'EPSG:4326',
        always_xy := true
    ) AS geom

FROM ST_Read('{tmp.name}')
""")

# =========================
# INDEX
# =========================

con.execute("""
CREATE INDEX idx_peb_geom
ON peb
USING RTREE (geom)
""")

print("Table PEB créée ✔")

# =========================
# CHECK
# =========================

result = con.execute("""
SELECT peb_zone, COUNT(*)
FROM peb
GROUP BY peb_zone
ORDER BY peb_zone
""").fetchall()

print(result)

con.close()

# suppression temp
os.unlink(tmp.name)