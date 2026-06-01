import duckdb
import pandas as pd
import streamlit as st
from pathlib import Path

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent

# BASE_DIR correspond à "data/app". 
# On utilise .parent pour remonter dans "data", puis on descend dans "src"
DB_PATH = BASE_DIR.parent / "src" / "SAE_601_IMO" / "immo_sae2026.db"
# --- FONCTIONS GLOBALES ---

@st.cache_data
def get_villes():
    """Récupère la liste dynamique des villes disponibles dans la base DVF."""
    con = duckdb.connect(str(DB_PATH), read_only=True)
    query = """
        SELECT DISTINCT nom_commune 
        FROM dvf 
        WHERE nom_commune IS NOT NULL 
        ORDER BY nom_commune
    """
    villes = con.execute(query).df()['nom_commune'].tolist()
    con.close()
    
    # On ajoute une option par défaut au début de la liste
    villes.insert(0, "Sélectionnez une ville...")
    return villes

# --- FONCTIONS MODE EXPLORATOIRE ---


@st.cache_data
def get_donnees_carte(ville, prix_max, peb_filtre, energies_dpe):
    """
    Croise DVF, DPE et PEB en fonction des choix de l'utilisateur.
    Utilise vos requêtes de jointures optimisées avec un typage fort.
    """
    if ville == "Sélectionnez une ville...":
        return pd.DataFrame()

    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.execute("INSTALL spatial; LOAD spatial;")

    if not energies_dpe:
        energies_dpe = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    dpe_tuple = tuple(energies_dpe) if len(energies_dpe) > 1 else f"('{energies_dpe[0]}')"

    peb_condition = "1=1"
    if peb_filtre == "Hors zone de bruit":
        peb_condition = "p.peb_zone IS NULL"
    elif peb_filtre == "Zone modérée":
        peb_condition = "p.peb_zone IN ('C', 'D')"

    # Ajout des TRY_CAST sur la latitude et longitude pour pouvoir faire des moyennes
    query = f"""
        SELECT 
            TRY_CAST(REPLACE(v.latitude, ',', '.') AS DOUBLE) AS latitude, 
            TRY_CAST(REPLACE(v.longitude, ',', '.') AS DOUBLE) AS longitude, 
            v.valeur_fonciere, 
            v.surface_reelle_bati,
            ROUND(
                TRY_CAST(REPLACE(v.valeur_fonciere, ',', '.') AS DOUBLE) / 
                NULLIF(TRY_CAST(v.surface_reelle_bati AS DOUBLE), 0)
            ) AS prix_m2,
            d.etiquette_dpe,
            COALESCE(p.peb_zone, 'Aucune') AS peb_zone
        FROM dvf v
        
        LEFT JOIN raw_dpe d 
            ON d.code_insee_ban = v.code_commune 
            -- AND d.adresse_normalisee = v.adresse_normalisee
            
        LEFT JOIN peb p 
            ON ST_Intersects(v.geom, p.geom)
            
        WHERE v.nom_commune = '{ville}'
          AND (
                TRY_CAST(REPLACE(v.valeur_fonciere, ',', '.') AS DOUBLE) / 
                NULLIF(TRY_CAST(v.surface_reelle_bati AS DOUBLE), 0)
              ) <= {prix_max}
          AND d.etiquette_dpe IN {dpe_tuple}
          AND {peb_condition}
          -- On s'assure que la conversion des coordonnées n'est pas nulle
          AND TRY_CAST(REPLACE(v.latitude, ',', '.') AS DOUBLE) IS NOT NULL
        
        LIMIT 5000
    """

    try:
        df = con.execute(query).df()
    except Exception as e:
        st.error(f"Erreur SQL : {e}")
        df = pd.DataFrame()

    con.close()
    return df
# --- FONCTIONS DATAVIZ (GRAPHIQUES) ---

@st.cache_data
def get_donnees_graphiques(choix_x, choix_y):
    """
    Génère les données agrégées pour les graphiques en traduisant
    les choix de l'utilisateur en requêtes SQL.
    """
    con = duckdb.connect(str(DB_PATH), read_only=True)
    
    # 1. Dictionnaires de traduction (Interface -> SQL)
    colonnes_x = {
        "Commune": "v.nom_commune",
        "Étiquette DPE": "d.etiquette_dpe",
        "Année de construction": "d.periode_construction"
    }
    
    colonnes_y = {
        "Prix moyen au m²": """
            ROUND(AVG(
                TRY_CAST(REPLACE(v.valeur_fonciere, ',', '.') AS DOUBLE) / 
                NULLIF(TRY_CAST(v.surface_reelle_bati AS DOUBLE), 0)
            ))
        """,
        "Volume de ventes": "COUNT(DISTINCT v.id_mutation)",
        "Surface moyenne": "ROUND(AVG(TRY_CAST(v.surface_reelle_bati AS DOUBLE)))"
    }

    # On récupère le vrai bout de code SQL correspondant aux choix
    sql_x = colonnes_x[choix_x]
    sql_y = colonnes_y[choix_y]

    # 2. Construction de la requête
    query = f"""
        SELECT 
            {sql_x} AS axe_x,
            {sql_y} AS axe_y
        FROM dvf v
        LEFT JOIN raw_dpe d 
            ON d.code_insee_ban = v.code_commune 
            -- AND d.adresse_normalisee = v.adresse_normalisee
            
        WHERE {sql_x} IS NOT NULL 
          AND {sql_x} != '' 
          AND {sql_x} != 'N/A'
          
        GROUP BY {sql_x}
        ORDER BY axe_x
    """

    try:
        df = con.execute(query).df()
        # On renomme les colonnes pour que le graphique Streamlit soit joli
        df = df.rename(columns={"axe_x": choix_x, "axe_y": choix_y})
    except Exception as e:
        st.error(f"Erreur SQL lors de la création du graphique : {e}")
        df = pd.DataFrame()

    con.close()
    return df
   

   # --- FONCTIONS INVESTISSEMENT ---

@st.cache_data
def get_opportunites_investissement(budget, surface_min, cout_renovation, dpe_cible):
    """
    Identifie les secteurs les plus rentables pour l'achat-rénovation.
    Calcule la différence entre le prix d'une passoire thermique + travaux
    et le prix de revente d'un bien avec le DPE cible.
    """
    con = duckdb.connect(str(DB_PATH), read_only=True)
    
    # 1. On construit la requête SQL (CTE - Common Table Expression)
    # On calcule d'abord les moyennes pour chaque ville
    query = f"""
        WITH stats_ville AS (
            SELECT 
                v.nom_commune,
                
                -- Prix moyen des passoires thermiques (F ou G)
                AVG(CASE WHEN d.etiquette_dpe IN ('F', 'G') THEN 
                    TRY_CAST(REPLACE(v.valeur_fonciere, ',', '.') AS DOUBLE) / 
                    NULLIF(TRY_CAST(v.surface_reelle_bati AS DOUBLE), 0)
                END) AS prix_m2_passoire,
                
                -- Prix moyen des biens déjà rénovés (Le DPE cible choisi)
                AVG(CASE WHEN d.etiquette_dpe = '{dpe_cible}' THEN 
                    TRY_CAST(REPLACE(v.valeur_fonciere, ',', '.') AS DOUBLE) / 
                    NULLIF(TRY_CAST(v.surface_reelle_bati AS DOUBLE), 0)
                END) AS prix_m2_renove
                
            FROM dvf v
            LEFT JOIN raw_dpe d ON d.code_insee_ban = v.code_commune
            GROUP BY v.nom_commune
        )
        
        -- 2. On filtre et on calcule la plus-value
        SELECT 
            nom_commune,
            ROUND(prix_m2_passoire) AS prix_achat_m2,
            ROUND(prix_m2_renove) AS prix_revente_m2,
            -- Formule : Prix revente - (Prix achat + Cout travaux)
            ROUND(prix_m2_renove - (prix_m2_passoire + {cout_renovation})) AS profit_m2_estime
        FROM stats_ville
        
        WHERE prix_m2_passoire IS NOT NULL 
          AND prix_m2_renove IS NOT NULL
          
          -- Le projet doit rentrer dans le budget de l'utilisateur
          AND (prix_m2_passoire + {cout_renovation}) * {surface_min} <= {budget}
          
          -- On ne garde que les villes où l'opération est rentable (profit > 0)
          AND (prix_m2_renove - (prix_m2_passoire + {cout_renovation})) > 0
          
        ORDER BY profit_m2_estime DESC
        LIMIT 5
    """

    try:
        df = con.execute(query).df()
    except Exception as e:
        st.error(f"Erreur SQL lors du calcul d'investissement : {e}")
        df = pd.DataFrame()

    con.close()
    return df