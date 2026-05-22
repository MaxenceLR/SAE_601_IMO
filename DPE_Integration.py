import requests
import pandas as pd
import duckdb


## RECUPERATION DES DONNEES ##

dataset = "dpe03existant"

url = f"https://data.ademe.fr/data-fair/api/v1/datasets/{dataset}/lines"

params = {
    "size": 1000,
    "page": 1
}

response = requests.get(url, params=params)

if response.status_code == 200:
    data = response.json()
    
    df = pd.DataFrame(data["results"])
    
    print(df.head())
    print(df.shape)

else:
    print("Erreur :", response.status_code)
    print(response.text)


## CREATION DE LA BASE ##

con = duckdb.connect("DPE.db")

con.execute("""
CREATE TABLE dpe (

    -- ======================
    -- IDENTIFIANTS
    -- ======================
    id VARCHAR,
    numero_dpe VARCHAR,
    identifiant_ban VARCHAR,

    -- ======================
    -- LOCALISATION
    -- ======================
    code_postal_brut VARCHAR,
    nom_commune_ban VARCHAR,
    code_insee_ban VARCHAR,
    code_departement_ban VARCHAR,

    -- coordonnées
    coor_x DOUBLE,
    coor_y DOUBLE,
    geopoint VARCHAR,

    -- ======================
    -- LOGEMENT
    -- ======================
    type_batiment VARCHAR,
    typologie_logement VARCHAR,
    surface_habitable_logement DOUBLE,
    surface_habitable_immeuble DOUBLE,
    nombre_niveau_logement INTEGER,
    nombre_niveau_immeuble INTEGER,
    nombre_appartement INTEGER,
    annee_construction INTEGER,

    -- ======================
    -- ÉNERGIE GLOBALE
    -- ======================
    conso_5_usages_ep DOUBLE,
    conso_5_usages_ef DOUBLE,
    emission_ges_5_usages DOUBLE,

    etiquette_dpe VARCHAR,
    etiquette_ges VARCHAR,

    -- ======================
    -- CHAUFFAGE
    -- ======================
    type_installation_chauffage VARCHAR,
    type_energie_principale_chauffage VARCHAR,
    conso_chauffage_ep DOUBLE,
    emission_ges_chauffage DOUBLE,
    cout_chauffage DOUBLE,

    -- ======================
    -- ECS (eau chaude)
    -- ======================
    type_installation_ecs VARCHAR,
    conso_ecs_ep DOUBLE,
    emission_ges_ecs DOUBLE,
    cout_ecs DOUBLE,

    -- ======================
    -- REFROIDISSEMENT
    -- ======================
    type_generateur_froid VARCHAR,
    conso_refroidissement_ep DOUBLE,
    emission_ges_refroidissement DOUBLE,

    -- ======================
    -- ISOLATION
    -- ======================
    qualite_isolation_murs VARCHAR,
    qualite_isolation_plancher_bas VARCHAR,
    qualite_isolation_menuiseries VARCHAR,
    isolation_toiture VARCHAR,

    -- ======================
    -- CONFORT / AUTRES
    -- ======================
    zone_climatique VARCHAR,
    classe_altitude VARCHAR,
    inertie_lourde BOOLEAN,
    indicateur_confort_ete VARCHAR,

    -- ======================
    -- BILAN GLOBAL
    -- ======================
    cout_total_5_usages DOUBLE,
    cout_total_5_usages_energie_n1 DOUBLE

)
""")

print("Table DPE créée ✔")

con.register("df_temp", df)

con.execute("""
INSERT INTO dpe
SELECT
    _id,
    numero_dpe,
    identifiant_ban,

    code_postal_brut,
    nom_commune_ban,
    code_insee_ban,
    code_departement_ban,

    coordonnee_cartographique_x_ban,
    coordonnee_cartographique_y_ban,
    _geopoint,

    type_batiment,
    typologie_logement,
    surface_habitable_logement,
    surface_habitable_immeuble,
    nombre_niveau_logement,
    nombre_niveau_immeuble,
    nombre_appartement,
    annee_construction,

    conso_5_usages_ep,
    conso_5_usages_ef,
    emission_ges_5_usages,

    etiquette_dpe,
    etiquette_ges,

    type_installation_chauffage,
    type_energie_principale_chauffage,
    conso_chauffage_ep,
    emission_ges_chauffage,
    cout_chauffage,

    type_installation_ecs,
    conso_ecs_ep,
    emission_ges_ecs,
    cout_ecs,

    type_generateur_froid,
    conso_refroidissement_ep,
    emission_ges_refroidissement,

    qualite_isolation_murs,
    qualite_isolation_plancher_bas,
    qualite_isolation_menuiseries,
    isolation_toiture,

    zone_climatique,
    classe_altitude,
    inertie_lourde,
    indicateur_confort_ete,

    cout_total_5_usages,
    cout_total_5_usages_energie_n1

FROM df_temp
""")

print("Insertion OK ✔")


