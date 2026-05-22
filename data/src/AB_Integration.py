import duckdb
import urllib.request
import os

print("🌍 Démarrage de l'intégration des frontières administratives (Admin Express)...")

# On s'assure que le dossier data existe
os.makedirs("data", exist_ok=True)

# Nouvelle URL fiable : Contours de toutes les communes françaises (simplifiés pour de meilleures perfs)
url_admin = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/communes-version-simplifiee.geojson"
fichier_local = "data/limites_administratives.geojson"

# SÉCURITÉ : On vérifie si le fichier actuel est un vrai GeoJSON valide. 
# S'il contient une erreur HTML (ex: 404), on le supprime pour forcer le retéléchargement.
if os.path.exists(fichier_local):
    try:
        import json
        with open(fichier_local, 'r', encoding='utf-8') as f:
            json.load(f)
    except Exception:
        print("🗑️ Fichier corrompu détecté (probablement une erreur 404). Suppression en cours...")
        os.remove(fichier_local)

if not os.path.exists(fichier_local):
    print("⬇️ Téléchargement des polygones géographiques (cela peut prendre quelques secondes)...")
    # Il est préférable de télécharger les fichiers spatiaux localement d'abord.
    # Les fichiers géographiques sont souvent lourds et complexes à lire en direct via le réseau.
    urllib.request.urlretrieve(url_admin, fichier_local)
    print("✅ Téléchargement terminé !")
else:
    print("✅ Le fichier spatial est déjà présent en local dans le dossier 'data'.")

print("🔌 Connexion à la base de données 'immo_bi_database.db'...")
con = duckdb.connect("immo_bi_database.db")

print("📦 Chargement de l'extension SPATIAL (indispensable pour lire les géométries)...")
# L'extension spatial donne à DuckDB le pouvoir de comprendre les cartes 
# (calculer des distances, vérifier si un point est dans un polygone, lire du GeoJSON/Shapefile)
con.execute("INSTALL spatial;")
con.execute("LOAD spatial;")

print("🗺️ Création de la table DIM_GEOGRAPHIE...")
con.execute("DROP TABLE IF EXISTS dim_geographie;")

# La fonction st_read() est le "couteau suisse" de DuckDB pour la géographie.
# Elle analyse le fichier, détecte automatiquement les colonnes et extrait la forme géométrique (geom).
con.execute(f"""
    CREATE TABLE dim_geographie AS 
    SELECT * FROM st_read('{fichier_local}');
""")

# On compte le nombre de polygones (communes/départements) créés
nb_polygones = con.execute("SELECT COUNT(*) FROM dim_geographie").fetchone()[0]

# On récupère le nom des colonnes pour voir ce que le fichier contenait
colonnes = [col[0] for col in con.execute("DESCRIBE dim_geographie").fetchall()]

print("\n" + "="*50)
print(f"✅ DIM_GEOGRAPHIE TERMINEE !")
print(f"📍 {nb_polygones:,.0f} entités géographiques ont été chargées avec succès.")
print(f"📋 Voici les 5 premières colonnes détectées : {', '.join(colonnes[:5])}")
print("="*50 + "\n")