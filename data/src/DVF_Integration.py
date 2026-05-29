import requests
import duckdb
import os

# ======================
# PATHS
# ======================

file_path = r"C:\temp\dvf.csv.gz"
db_path = r"C:\temp\dvf.db"

os.makedirs(r"C:\temp", exist_ok=True)

# ======================
# DOWNLOAD
# ======================

url = "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres-geolocalisees/20260424-090024/dvf.csv.gz"

print("Téléchargement DVF...")

response = requests.get(url, stream=True)

with open(file_path, "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)

print("Téléchargement terminé ✔")

# ======================
# DUCKDB
# ======================

con = duckdb.connect(db_path)

con.execute("INSTALL spatial")
con.execute("LOAD spatial")

con.execute("DROP TABLE IF EXISTS dvf")

con.execute("""
CREATE TABLE dvf AS
SELECT *,
       ST_Point(
            CAST(longitude AS DOUBLE),
            CAST(latitude AS DOUBLE)
       ) AS geom
FROM read_csv_auto(
    'C:/temp/dvf.csv.gz',
    all_varchar=true,
    ignore_errors=true
)
WHERE latitude IS NOT NULL
AND longitude IS NOT NULL
""")

print("Import DVF terminé ✔")

print(
    con.execute("SELECT COUNT(*) FROM dvf").fetchall()
)