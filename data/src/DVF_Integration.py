import requests
import pandas as pd
import duckdb
import gzip
import shutil
import os

## ======================
## 1. TELECHARGEMENT
## ======================

url = "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres-geolocalisees/20260424-090024/dvf.csv.gz"

file_gz = "dvf.csv.gz"
file_csv = "dvf.csv"

print("Téléchargement DVF...")

response = requests.get(url, stream=True)

with open(file_gz, "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)

print("Téléchargement terminé ✔")

## ======================
## 2. DECOMPRESSION
## ======================

print("Décompression...")

with gzip.open(file_gz, "rb") as f_in:
    with open(file_csv, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)

print("Décompression terminée ✔")


## ======================
## 3. LECTURE PANDAS
## ======================

print("Chargement CSV...")

df = pd.read_csv(file_csv, low_memory=False)

print(df.head())
print(df.shape)


## ======================
## 4. CREATION DU DUCKDB
## ======================

con = duckdb.connect("DVF.db")

con.execute("""
CREATE TABLE dvf (
    id_mutation VARCHAR,
    date_mutation DATE,
    nature_mutation VARCHAR,
    valeur_fonciere DOUBLE,
    adresse_numero VARCHAR,
    adresse_nom_voie VARCHAR,
    code_postal VARCHAR,
    nom_commune VARCHAR,
    code_departement VARCHAR,
    type_local VARCHAR,
    surface_reelle_bati DOUBLE,
    nombre_pieces_principales INTEGER,
    longitude DOUBLE,
    latitude DOUBLE
)
""")

print("Table DVF créée ✔")


## ======================
## 5. INSERT DATA
## ======================

con.register("df_temp", df)

con.execute("""
INSERT INTO dvf
SELECT
    id_mutation,
    date_mutation,
    nature_mutation,
    valeur_fonciere,
    adresse_numero,
    adresse_nom_voie,
    code_postal,
    nom_commune,
    code_departement,
    type_local,
    surface_reelle_bati,
    nombre_pieces_principales,
    longitude,
    latitude
FROM df_temp
""")

print("Insertion OK ✔")