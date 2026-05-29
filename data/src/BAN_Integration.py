import duckdb
import os
import time
from pathlib import Path

def importer_donnees(dept):
    print(f"Démarrage de l'ETL BAN pour le département {dept}...")

    BASE_DIR = Path(__file__).resolve().parent
    db_path = BASE_DIR / "SAE_601_IMO" / "immo_sae2026.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path))

    con.execute("INSTALL httpfs; LOAD httpfs;")
    
    con.execute("""
        CREATE TABLE IF NOT EXISTS dim_ban (
            id VARCHAR, numero VARCHAR, rep VARCHAR, nom_voie VARCHAR,
            code_postal VARCHAR, code_insee VARCHAR, nom_commune VARCHAR,
            lon DOUBLE, lat DOUBLE
        );
    """)

    # Nettoyage préalable corrigé (uniquement avec code_insee)
    con.execute(f"DELETE FROM dim_ban WHERE code_insee LIKE '{dept}%';")

    start_time = time.time()
    
    # URL ciblée uniquement sur le département choisi
    url = f"https://adresse.data.gouv.fr/data/ban/adresses/latest/csv/adresses-{dept}.csv.gz"

    try:
        con.execute(f"""
            INSERT INTO dim_ban 
            SELECT 
                id, numero, rep, nom_voie, code_postal, 
                code_insee, nom_commune, lon, lat 
            FROM read_csv_auto('{url}', delim=';', header=True, ignore_errors=true)
        """)
        nb_adresses = con.execute(f"SELECT COUNT(*) FROM dim_ban WHERE code_insee LIKE '{dept}%'").fetchone()[0]
        
        print("\n" + "="*50)
        print(f"DIM_BAN TERMINEE POUR LE {dept} !")
        print(f"{nb_adresses:,.0f} adresses chargées en {round(time.time() - start_time, 2)}s.")
        print("="*50 + "\n")
    except Exception as e:
        print(f"Erreur lors de l'intégration du département {dept} : {e}")
    finally:
        con.close()

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    dept = os.getenv("DEPARTEMENT_CIBLE", "44")
    importer_donnees(dept)