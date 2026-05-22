import duckdb

# ======================
# CONFIGURATION
# ======================
db_path = r"C:\temp\dvf.db"

con = duckdb.connect(db_path)

# ======================
# 1. EXTENSION SPATIAL
# ======================
print("Chargement extension spatial DuckDB...")
con.execute("INSTALL spatial;")
con.execute("LOAD spatial;")
print("Extension spatial chargée ✔")

# ======================
# 2. VÉRIFICATION DES TABLES
# ======================
tables = con.execute("SHOW TABLES").fetchdf()
print("Tables disponibles :", tables["name"].tolist())

# ======================
# 3. CRÉATION TABLE DVF AVEC GÉOMÉTRIE
# ======================
print("\nCréation table dvf_geo...")
con.execute("DROP TABLE IF EXISTS dvf_geo")
con.execute("""
CREATE TABLE dvf_geo AS
SELECT *,
    ST_Point(
        TRY_CAST(REPLACE(longitude, ',', '.') AS DOUBLE),
        TRY_CAST(REPLACE(latitude,  ',', '.') AS DOUBLE)
    ) AS geom
FROM dvf
WHERE latitude IS NOT NULL
  AND longitude IS NOT NULL
  AND latitude  <> ''
  AND longitude <> ''
""")

count_dvf = con.execute("SELECT COUNT(*) FROM dvf_geo WHERE geom IS NOT NULL").fetchone()[0]
print(f"Lignes DVF avec géométrie valide : {count_dvf:,} ✔")

# ======================
# 4. CRÉATION TABLE PEB AVEC GÉOMÉTRIE
# ======================
# Le GeoJSON DGAC est en Lambert-93 (EPSG:2154) — coordonnées ~508000, 6860000
# DVF est en WGS84 (EPSG:4326) → on reprojette PEB pour aligner les deux
print("\nCréation table peb_geo (reprojection Lambert-93 → WGS84)...")
con.execute("DROP TABLE IF EXISTS peb_geo")
con.execute("""
CREATE TABLE peb_geo AS
SELECT
    zone, code_oaci, nom, producteur, ref_doc,
    indldenext, indldenint, date_arret, date_maj, id_map, geometry,
    ST_Transform(
        ST_GeomFromGeoJSON(geometry),
        'EPSG:2154',
        'EPSG:4326'
    ) AS geom
FROM peb
WHERE geometry IS NOT NULL AND geometry <> ''
""")

count_peb = con.execute("SELECT COUNT(*) FROM peb_geo WHERE geom IS NOT NULL").fetchone()[0]
print(f"Zones PEB avec géométrie valide : {count_peb:,} ✔")

# ======================
# 5. JOINTURE SPATIALE
# ======================
# ST_Within(point_dvf, polygon_peb) → vrai si la vente est dans une zone PEB
print("\nJointure spatiale DVF ∩ PEB en cours (peut prendre quelques minutes)...")

con.execute("DROP TABLE IF EXISTS dvf_en_zone_peb")
con.execute("""
CREATE TABLE dvf_en_zone_peb AS
SELECT
    -- Champs DVF clés
    d.id_mutation,
    d.date_mutation,
    d.nature_mutation,
    d.valeur_fonciere,
    d.adresse_numero,
    d.adresse_nom_voie,
    d.code_postal,
    d.nom_commune,
    d.code_departement,
    d.type_local,
    d.surface_reelle_bati,
    d.nombre_pieces_principales,
    d.latitude,
    d.longitude,
    -- Champs PEB
    p.zone        AS peb_zone,
    p.nom         AS peb_nom_aeroport,
    p.code_oaci   AS peb_code_oaci,
    p.date_arret  AS peb_date_arret,
    p.ref_doc     AS peb_ref_doc
FROM dvf_geo d
JOIN peb_geo p
  ON ST_Within(d.geom, p.geom)
""")

count_result = con.execute("SELECT COUNT(*) FROM dvf_en_zone_peb").fetchone()[0]
print(f"Transactions DVF en zone PEB : {count_result:,} ✔")

# ======================
# 6. STATISTIQUES PAR ZONE
# ======================
print("\n--- Répartition par zone PEB ---")
stats = con.execute("""
SELECT
    peb_zone,
    peb_nom_aeroport,
    COUNT(*)                                        AS nb_transactions,
    ROUND(AVG(TRY_CAST(REPLACE(valeur_fonciere, ',', '.') AS DOUBLE)), 0) AS prix_moyen
FROM dvf_en_zone_peb
GROUP BY peb_zone, peb_nom_aeroport
ORDER BY nb_transactions DESC
""").fetchdf()
print(stats.to_string(index=False))

# ======================
# 7. EXPORT CSV
# ======================
output_csv = r"C:\temp\dvf_en_zone_peb.csv"
con.execute(f"""
COPY dvf_en_zone_peb TO '{output_csv}' (HEADER, DELIMITER ';')
""")
print(f"\nExport CSV : {output_csv} ✔")

print("\nTerminé ✔")
con.close()