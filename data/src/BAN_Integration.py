import duckdb
import os
import time

print("🚀 Démarrage de l'ETL (Initialisation de la base de données)...")

# =========================
# BASE UNIQUE (DVF + PEB + BAN)
# =========================

db_path = r"C:\temp\SAE_601_IMO\data\src\SAE_601_IMO\immo_sae2026.db"

os.makedirs(os.path.dirname(db_path), exist_ok=True)

con = duckdb.connect(db_path)

# ==============================================================================
# ÉTAPE 1 : INSTALLATION DES EXTENSIONS DUCKDB
# ==============================================================================
# httpfs permet à DuckDB de lire des fichiers directement depuis une URL (https://)
print("📦 Chargement de l'extension réseau (httpfs)...")
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")

# =========================
# BAN TABLE
# =========================

# ==============================================================================
# ÉTAPE 2 : INTÉGRATION DE LA BAN (Base Adresse Nationale)
# ==============================================================================
print("\n🌍 Création de la table DIM_BAN (Référentiel Spatial)...")
con.execute("DROP TABLE IF EXISTS dim_ban;")

con.execute("""
    CREATE TABLE dim_ban (
        id VARCHAR,
        numero VARCHAR,
        rep VARCHAR,
        nom_voie VARCHAR,
        code_postal VARCHAR,
        code_insee VARCHAR,
        nom_commune VARCHAR,
        lon DOUBLE,
        lat DOUBLE
    );
""")

print("🗺️ Génération de la liste complète des départements français...")

departements = [f"{i:02d}" for i in range(1, 96) if i != 20]
departements.extend(["2A", "2B"])
departements.extend(["971", "972", "973", "974", "976"])
departements.sort()

print(f"⬇️  Téléchargement et ingestion pour {len(departements)} départements programmés.")

start_time = time.time()
erreurs = []

# =========================
# INGESTION BAN
# =========================

for dept in departements:
    print(f"➡️ {dept}")

    url = f"https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-{dept}.csv.gz"

    try:
        con.execute(f"""
            INSERT INTO dim_ban 
            SELECT 
                id, numero, rep, nom_voie, code_postal, 
                code_insee, nom_commune, lon, lat 
            FROM read_csv_auto(
                '{url}',
                delim=';',
                header=True,
                ignore_errors=true
            )
        """)
    except Exception as e:
        print(f"❌ erreur {dept}")
        erreurs.append(dept)

# =========================
# CHECK
# =========================

nb_adresses = con.execute("SELECT COUNT(*) FROM dim_ban").fetchone()[0]
duree_minutes = round((time.time() - start_time) / 60, 2)

print("\n" + "="*50)
print(f"✅ DIM_BAN (NATIONALE) TERMINEE !")
print(f"🏠 {nb_adresses:,.0f} adresses géolocalisées ont été chargées.")
print(f"⏱️ Temps total de traitement : {duree_minutes} minutes.")
if erreurs:
    print(f"⚠️ Les départements suivants ont échoué (souvent un timeout réseau) : {erreurs}")
print("="*50 + "\n")

print("="*50)
con.close()