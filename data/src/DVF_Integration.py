import requests
import duckdb
from pathlib import Path

# ======================
# PATHS (ROBUSTE & PORTABLE)
# ======================

base_path = Path(__file__).resolve().parent / "SAE_601_IMO"
file_path = base_path / "dvf.csv.gz"
db_path = base_path / "immo_sae2026.db"

base_path.mkdir(exist_ok=True)

print("📁 Dossier base :", base_path)
print("🗄️ Base de données :", db_path)

# ======================
# DOWNLOAD DVF
# ======================

url = "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres-geolocalisees/20260424-090024/dvf.csv.gz"

print("⬇️ Téléchargement DVF...")

response = requests.get(url, stream=True)

with open(file_path, "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            f.write(chunk)

print("✔ Téléchargement terminé")

# ======================
# DUCKDB
# ======================

con = duckdb.connect(str(db_path))

con.execute("INSTALL spatial")
con.execute("LOAD spatial")

con.execute("DROP TABLE IF EXISTS dvf")

print("📊 Import DVF en cours...")

con.execute(f"""
CREATE TABLE dvf AS
SELECT *,
       ST_Point(
            CAST(longitude AS DOUBLE),
            CAST(latitude AS DOUBLE)
       ) AS geom
FROM read_csv_auto(
    '{str(file_path).replace("\\", "/")}',
    all_varchar=true,
    ignore_errors=true
)
WHERE latitude IS NOT NULL
AND longitude IS NOT NULL
""")

print("✔ Import terminé")

# ======================
# CHECK
# ======================

print("📌 Nombre de lignes :", con.execute("SELECT COUNT(*) FROM dvf").fetchall())
print("📂 Fichiers créés dans :", list(base_path.glob("*")))