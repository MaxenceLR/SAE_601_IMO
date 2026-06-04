import duckdb
import pandas as pd
import streamlit as st
from pathlib import Path

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "src" / "SAE_601_IMO" / "immo_sae2026.db"

# --- REQUÊTE COMMUNE (VILLES) ---
@st.cache_data
def get_villes():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    query = "SELECT DISTINCT nom_commune FROM biens_optimises WHERE nom_commune IS NOT NULL ORDER BY nom_commune"
    villes = con.execute(query).df()['nom_commune'].tolist()
    con.close()
    villes.insert(0, "Sélectionnez une ville...")
    return villes

# --- 1. MODE EXPLORATOIRE (CARTE) ---
@st.cache_data
def get_donnees_carte(ville, prix_max, peb_filtre, energies_dpe):
    if ville == "Sélectionnez une ville...":
        return pd.DataFrame()

    con = duckdb.connect(str(DB_PATH), read_only=True)

    if not energies_dpe:
        energies_dpe = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    dpe_tuple = tuple(energies_dpe) if len(energies_dpe) > 1 else f"('{energies_dpe[0]}')"

    peb_condition = "1=1"
    if peb_filtre == "Hors zone de bruit":
        peb_condition = "peb_zone = 'Aucune'"
    elif peb_filtre == "Zone modérée":
        peb_condition = "peb_zone IN ('C', 'D')"

    query = f"""
        SELECT latitude, longitude, valeur_fonciere, surface, prix_m2, etiquette_dpe, peb_zone
        FROM biens_optimises
        WHERE nom_commune = '{ville}'
          AND prix_m2 <= {prix_max}
          AND etiquette_dpe IN {dpe_tuple}
          AND {peb_condition}
        LIMIT 5000
    """
    df = con.execute(query).df()
    con.close()
    return df

# --- 2. DATAVIZ (GRAPHIQUES) ---
@st.cache_data
def get_donnees_graphiques(choix_x, choix_y):
    con = duckdb.connect(str(DB_PATH), read_only=True)
    
    colonnes_x = {"Commune": "nom_commune", "Étiquette DPE": "etiquette_dpe", "Année de construction": "periode_construction"}
    colonnes_y = {"Prix moyen au m²": "ROUND(AVG(prix_m2))", "Volume de ventes": "COUNT(*)", "Surface moyenne": "ROUND(AVG(surface))"}

    sql_x = colonnes_x[choix_x]
    sql_y = colonnes_y[choix_y]

    query = f"""
        SELECT {sql_x} AS axe_x, {sql_y} AS axe_y FROM biens_optimises
        WHERE {sql_x} IS NOT NULL AND {sql_x} NOT IN ('', 'N/A')
        GROUP BY {sql_x} ORDER BY axe_x
    """
    df = con.execute(query).df().rename(columns={"axe_x": choix_x, "axe_y": choix_y})
    con.close()
    return df

# --- 3. INVESTISSEMENT ---
@st.cache_data
def get_opportunites_investissement(budget, surface_min, cout_renovation, dpe_cible):
    con = duckdb.connect(str(DB_PATH), read_only=True)
    query = f"""
        WITH stats_ville AS (
            SELECT 
                nom_commune,
                AVG(CASE WHEN etiquette_dpe IN ('F', 'G') THEN prix_m2 END) AS prix_m2_passoire,
                AVG(CASE WHEN etiquette_dpe = '{dpe_cible}' THEN prix_m2 END) AS prix_m2_renove
            FROM biens_optimises GROUP BY nom_commune
        )
        SELECT 
            nom_commune,
            ROUND(prix_m2_passoire) AS prix_achat_m2,
            ROUND(prix_m2_renove) AS prix_revente_m2,
            ROUND(prix_m2_renove - (prix_m2_passoire + {cout_renovation})) AS profit_m2_estime
        FROM stats_ville
        WHERE prix_m2_passoire IS NOT NULL AND prix_m2_renove IS NOT NULL
          AND (prix_m2_passoire + {cout_renovation}) * {surface_min} <= {budget}
          AND (prix_m2_renove - (prix_m2_passoire + {cout_renovation})) > 0
        ORDER BY profit_m2_estime DESC LIMIT 5
    """
    df = con.execute(query).df()
    con.close()
    return df