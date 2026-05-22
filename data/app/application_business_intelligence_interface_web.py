import duckdb
import os
import time

print("🚀 Démarrage de l'ETL (Initialisation de la base de données)...")

# 1. Création du dossier 'data' (même si on utilise le web, c'est une bonne pratique)
os.makedirs("data", exist_ok=True)

# 2. Création et connexion à la base de données locale
con = duckdb.connect("immo_bi_database.db")

# ==============================================================================
# ÉTAPE 1 : INSTALLATION DES EXTENSIONS DUCKDB
# ==============================================================================
# httpfs permet à DuckDB de lire des fichiers directement depuis une URL (https://)
print("Chargement de l'extension réseau (httpfs)...")
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")


# ==============================================================================
# ÉTAPE 2 : INTÉGRATION DE LA BAN (Base Adresse Nationale)
# ==============================================================================
print("\nCréation de la table DIM_BAN (Référentiel Spatial)...")
con.execute("DROP TABLE IF EXISTS dim_ban;")

# Création de la structure de la table pour les adresses
con.execute("""
    CREATE TABLE dim_ban (
        id VARCHAR,
        numero VARCHAR,
        rep VARCHAR,        -- Répétition (bis, ter...)
        nom_voie VARCHAR,
        code_postal VARCHAR,
        code_insee VARCHAR,
        nom_commune VARCHAR,
        lon DOUBLE,         -- Longitude (X)
        lat DOUBLE          -- Latitude (Y)
    );
""")

print("Génération de la liste complète des départements français...")

# 1. Départements métropolitains de 01 à 95 (en excluant temporairement la Corse 20)
departements = [f"{i:02d}" for i in range(1, 96) if i != 20]

# 2. Ajout spécifique de la Corse
departements.extend(["2A", "2B"])

# 3. Ajout des DOM (Départements d'Outre-Mer)
departements.extend(["971", "972", "973", "974", "976"])

# Tri de la liste pour que l'exécution soit propre dans les logs
departements.sort()

print(f"Téléchargement et ingestion pour {len(departements)} départements programmés.")

start_time = time.time()
erreurs = [] # Pour stocker les éventuels départements qui échouent (ex: erreur réseau temporaire)

for dept in departements:
    print(f"  -> Traitement du département {dept} en cours...")
    url = f"https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-{dept}.csv.gz"
    
    try:
        # La magie de DuckDB : téléchargement et insertion à la volée
        con.execute(f"""
            INSERT INTO dim_ban 
            SELECT id, numero, rep, nom_voie, code_postal, code_insee, nom_commune, lon, lat 
            FROM read_csv_auto('{url}', delim=';', header=True, ignore_errors=true)
        """)
    except Exception as e:
        print(f"  Erreur lors du téléchargement du département {dept}. Il sera ignoré.")
        erreurs.append(dept)

nb_adresses = con.execute("SELECT COUNT(*) FROM dim_ban").fetchone()[0]
duree_minutes = round((time.time() - start_time) / 60, 2)

print("\n" + "="*50)
print(f"✅ DIM_BAN (NATIONALE) TERMINEE !")
print(f"🏠 {nb_adresses:,.0f} adresses géolocalisées ont été chargées.")
print(f"⏱️ Temps total de traitement : {duree_minutes} minutes.")
if erreurs:
    print(f" Les départements suivants ont échoué (souvent un timeout réseau) : {erreurs}")
print("="*50 + "\n")

# 💡 ASTUCE : Pour toute la France, il faudrait générer une liste de "01" à "95", "2A", "2B".
# Pour l'instant, on limite à la Bretagne / Pays de la Loire pour la maquette.
departements = ["44", "56"] 

print(f"  Téléchargement et ingestion des adresses pour les départements : {departements}")

start_time = time.time()

for dept in departements:
    print(f"  -> Traitement du département {dept} en cours (cela peut prendre quelques secondes)...")
    url = f"https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-{dept}.csv.gz"
    
    # La magie de DuckDB : Il va chercher le CSV compressé sur internet et l'insère directement
    # Le délimiteur de la BAN est le point-virgule (;)
    con.execute(f"""
        INSERT INTO dim_ban 
        SELECT id, numero, rep, nom_voie, code_postal, code_insee, nom_commune, lon, lat 
        FROM read_csv_auto('{url}', delim=';', header=True, ignore_errors=true)
    """)

nb_adresses = con.execute("SELECT COUNT(*) FROM dim_ban").fetchone()[0]
print(f"DIM_BAN terminée ! {nb_adresses:,} adresses géolocalisées ont été chargées en {round(time.time() - start_time, 2)} secondes.")


# ==============================================================================
# ÉTAPE 3 : TABLE DES FAITS (VENTES) - DONNÉES DE TEST TEMPORAIRES
# ==============================================================================
print("\nCréation de la table FAIT_VENTES...")
con.execute("""
    CREATE TABLE IF NOT EXISTS fait_ventes (
        id_mutation VARCHAR,
        code_commune VARCHAR,
        valeur_fonciere DOUBLE,
        surface_reelle_bati DOUBLE,
        prix_m2 DOUBLE
    );
""")

con.execute("DELETE FROM fait_ventes WHERE id_mutation LIKE 'TEST_%'")

# Injection de nos données de test pour ne pas casser la maquette de l'application
con.execute("""
    INSERT INTO fait_ventes VALUES 
    ('TEST_1', '56000', 250000, 100, 2500), -- Vannes
    ('TEST_2', '56000', 300000, 100, 3000), -- Vannes
    ('TEST_3', '56400', 200000, 100, 2000), -- Plumergat
    ('TEST_4', '44000', 350000, 100, 3500); -- Nantes
""")

print("\n Base de données 'immo_bi_database.db' mise à jour avec succès ! Prêt pour l'étape suivante.")