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

    # Ajout des colonnes secteur_lat et secteur_lon
    query = f"""
        SELECT 
            latitude, 
            longitude, 
            valeur_fonciere, 
            surface, 
            prix_m2, 
            etiquette_dpe, 
            peb_zone,
            ROUND(latitude, 2) AS secteur_lat,
            ROUND(longitude, 2) AS secteur_lon
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

    # Modification ici : ORDER BY axe_y DESC pour l'ordre décroissant
    # LIMIT 50 pour éviter de faire planter le graphique avec des milliers de communes
    query = f"""
        SELECT {sql_x} AS axe_x, {sql_y} AS axe_y FROM biens_optimises
        WHERE {sql_x} IS NOT NULL AND {sql_x} NOT IN ('', 'N/A')
        GROUP BY {sql_x} 
        ORDER BY axe_y DESC
        LIMIT 50
    """
    df = con.execute(query).df().rename(columns={"axe_x": choix_x, "axe_y": choix_y})
    con.close()
    return df

# --- 3. INVESTISSEMENT : ACHAT STRATÉGIQUE (Profil Investisseur) ---
@st.cache_data
def get_recommandations_achat(budget_max, surface_min, energies, strategie, choix_littoral):
    con = duckdb.connect(str(DB_PATH), read_only=True)
    
    dpe_tuple = tuple(energies) if len(energies) > 1 else (f"('{energies[0]}')" if energies else "('A','B','C','D')")
    
    # 1. On liste les communes du littoral de la Loire-Atlantique
    villes_littoral = "('La Baule-Escoublac', 'Pornichet', 'Le Pouliguen', 'Batz-sur-Mer', 'Le Croisic', 'La Turballe', 'Piriac-sur-Mer', 'Mesquer', 'Saint-Nazaire', 'Saint-Brevin-les-Pins', 'Pornic', 'La Plaine-sur-Mer', 'Préfailles', 'Saint-Michel-Chef-Chef', 'Les Moutiers-en-Retz')"
    
    # Construction du filtre littoral
    filtre_geo = "1=1"
    if choix_littoral == "🌊 Littoral uniquement":
        filtre_geo = f"nom_commune IN {villes_littoral}"
    elif choix_littoral == "🌳 Terres / Rétro-littoral":
        filtre_geo = f"nom_commune NOT IN {villes_littoral}"

    # 2. On adapte le tri (ORDER BY) selon la stratégie choisie
    if "Patrimonial" in strategie:
        tri_sql = "prix_moyen_m2 DESC" # On cherche les zones prisées et chères
        categorie_nom = "'Patrimonial'"
    elif "Rendement" in strategie:
        tri_sql = "prix_moyen_m2 ASC"  # On cherche les villes les moins chères (meilleur ROI potentiel)
        categorie_nom = "'Rendement'"
    else:
        tri_sql = "volume_ventes DESC" # On cherche les secteurs les plus dynamiques/liquides
        categorie_nom = "'Équilibré'"

    query = f"""
        WITH stats AS (
            SELECT 
                nom_commune,
                AVG(latitude) as lat,
                AVG(longitude) as lon,
                COUNT(*) as volume_ventes,
                ROUND(AVG(prix_m2)) as prix_moyen_m2
            FROM biens_optimises
            WHERE etiquette_dpe IN {dpe_tuple} 
              AND {filtre_geo}
            GROUP BY nom_commune
            HAVING COUNT(*) > 5
        ),
        categories AS (
            SELECT 
                *,
                (prix_moyen_m2 * {surface_min}) as budget_estime,
                CASE 
                    WHEN (prix_moyen_m2 * {surface_min}) > {budget_max} THEN 'À Fuir (Hors Budget)'
                    ELSE {categorie_nom}
                END as categorie
            FROM stats
        )
        -- On sélectionne le Top 5 des communes qui matchent la stratégie
        SELECT * FROM (
            SELECT * FROM categories WHERE categorie != 'À Fuir (Hors Budget)' ORDER BY {tri_sql} LIMIT 5
        )
        UNION ALL
        -- On garde toujours 1 ou 2 villes à fuir pour montrer où ne pas aller
        SELECT * FROM (
            SELECT * FROM categories WHERE categorie = 'À Fuir (Hors Budget)' ORDER BY budget_estime DESC LIMIT 2
        )
    """
    df = con.execute(query).df()
    con.close()
    return df


# --- 4. INVESTISSEMENT : RÉNOVATION (Analyse par "Quartier" de 1km²) ---
@st.cache_data
def get_opportunites_renovation(budget, surface_min, cout_renovation, dpe_cible, peb_filtre):
    con = duckdb.connect(str(DB_PATH), read_only=True)
    
    peb_condition = "1=1"
    if peb_filtre == "Hors zone de bruit":
        peb_condition = "peb_zone = 'Aucune'"
    elif peb_filtre == "Zone modérée":
        peb_condition = "peb_zone IN ('C', 'D')"

    # Valeur verte : Estimation de la plus-value selon le DPE final
    if dpe_cible in ['A', 'B']:
        prime_revente = 1.10
    elif dpe_cible == 'C':
        prime_revente = 1.05
    else:
        prime_revente = 1.00

    query = f"""
        WITH stats_quartier AS (
            SELECT 
                nom_commune,
                -- Astuce spatiale : on arrondit à 2 décimales pour créer des zones d'environ 1 km²
                ROUND(latitude, 2) AS secteur_lat,
                ROUND(longitude, 2) AS secteur_lon,
                ROUND(AVG(prix_m2)) AS prix_moyen_m2,
                COUNT(*) AS volume_ventes
            FROM biens_optimises 
            WHERE {peb_condition} 
              AND latitude IS NOT NULL 
              AND longitude IS NOT NULL
            GROUP BY nom_commune, ROUND(latitude, 2), ROUND(longitude, 2)
            HAVING COUNT(*) >= 5 -- Il faut au moins 5 ventes dans ce km² pour que la moyenne soit fiable
        ),
        simulation AS (
            SELECT 
                nom_commune,
                secteur_lat,
                secteur_lon,
                ROUND(prix_moyen_m2 * 0.85) AS prix_achat_m2,
                ROUND(prix_moyen_m2 * {prime_revente}) AS prix_revente_m2
            FROM stats_quartier
        )
        SELECT 
            -- On combine le nom de la ville et les coordonnées pour l'affichage texte
            nom_commune || ' (Zone ' || CAST(secteur_lat AS VARCHAR) || ', ' || CAST(secteur_lon AS VARCHAR) || ')' AS nom_commune,
            secteur_lat, -- NOUVEAU : On garde la latitude pour la carte
            secteur_lon, -- NOUVEAU : On garde la longitude pour la carte
            prix_achat_m2,
            prix_revente_m2,
            (prix_revente_m2 - (prix_achat_m2 + {cout_renovation})) AS profit_m2_estime
        FROM simulation
        WHERE (prix_achat_m2 + {cout_renovation}) * {surface_min} <= {budget}
          AND (prix_revente_m2 - (prix_achat_m2 + {cout_renovation})) > 0
        ORDER BY profit_m2_estime DESC 
        LIMIT 10
    """
    df = con.execute(query).df()
    con.close()
    return df