import duckdb
from pathlib import Path
import time

def optimiser_base_donnees():
    print("🚀 Démarre la création de la table optimisée (Data Mart)...")
    t0 = time.perf_counter()
    
    BASE_DIR = Path(__file__).resolve().parent
    db_path = BASE_DIR / "SAE_601_IMO" / "immo_sae2026.db"
    
    con = duckdb.connect(str(db_path))
    
    try:
        # Activer l'extension spatiale pour la jointure PEB
        con.execute("INSTALL spatial; LOAD spatial;")
        
        # 1. Nettoyage et création de la table Or (biens_optimises)
        con.execute("DROP TABLE IF EXISTS biens_optimises;")
        
        query_table = """
            CREATE TABLE biens_optimises AS
            SELECT 
                v.id_mutation,
                v.nom_commune,
                v.code_commune,
                TRY_CAST(REPLACE(v.valeur_fonciere, ',', '.') AS DOUBLE) AS valeur_fonciere,
                TRY_CAST(v.surface_reelle_bati AS DOUBLE) AS surface,
                ROUND(
                    TRY_CAST(REPLACE(v.valeur_fonciere, ',', '.') AS DOUBLE) / 
                    NULLIF(TRY_CAST(v.surface_reelle_bati AS DOUBLE), 0)
                ) AS prix_m2,
                TRY_CAST(REPLACE(v.latitude, ',', '.') AS DOUBLE) AS latitude,
                TRY_CAST(REPLACE(v.longitude, ',', '.') AS DOUBLE) AS longitude,
                d.etiquette_dpe,
                d.periode_construction,
                COALESCE(p.peb_zone, 'Aucune') AS peb_zone
            FROM dvf v
            LEFT JOIN raw_dpe d 
                ON d.code_insee_ban = v.code_commune 
            LEFT JOIN peb p 
                ON ST_Intersects(v.geom, p.geom)
            WHERE TRY_CAST(REPLACE(v.latitude, ',', '.') AS DOUBLE) IS NOT NULL
              AND v.valeur_fonciere IS NOT NULL
              AND v.surface_reelle_bati IS NOT NULL;
        """
        print(" -> Fusion des tables et calculs géographiques en cours...")
        con.execute(query_table)
        
        # 2. L'arme secrète de DuckDB : Les Index
        # Un index permet à DuckDB de trouver une ville instantanément sans relire toute la table
        print(" -> Création des index de performance...")
        con.execute("CREATE INDEX IF NOT EXISTS idx_commune ON biens_optimises(nom_commune);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_dpe ON biens_optimises(etiquette_dpe);")

        print("\n" + "="*50)
        print("✅ PIPELINE D'OPTIMISATION TERMINÉ !")
        print(f"Base de données accélérée en {time.perf_counter() - t0:.1f}s")
        print("="*50 + "\n")

    finally:
        con.close()

if __name__ == "__main__":
    optimiser_base_donnees()