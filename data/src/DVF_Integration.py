import requests
import duckdb
import os

# ======================
# 1. DOSSIER LOCAL SAFE
# ======================
file_path = r"C:\temp\dvf.csv.gz"
db_path = r"C:\temp\dvf.db"

os.makedirs(r"C:\temp", exist_ok=True)

# ======================
# 2. DOWNLOAD
# ======================
url = "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres-geolocalisees/20260424-090024/dvf.csv.gz"

print("Téléchargement DVF...")

response = requests.get(url, stream=True)

with open(file_path, "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)

print("Téléchargement terminé ✔")

# ======================
# 3. DUCKDB
# ======================
print("Création base DuckDB...")

con = duckdb.connect(db_path)
con.execute("""
drop table if exists dvf
""")
con.execute("""
CREATE TABLE dvf AS
SELECT *
FROM read_csv_auto(
    'C:/temp/dvf.csv.gz',
    all_varchar=true,
    ignore_errors=true
)
""")
print("Import terminé ✔")

result = con.execute("""
select * from dvf limit 5
""").fetchdf()

print(result)