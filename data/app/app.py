import streamlit as st
import streamlit.components.v1 as components
import json
import folium
from streamlit_folium import st_folium
import duckdb

# Configuration de la page en mode large
st.set_page_config(page_title="Cherche Ton Logement", page_icon="📍", layout="wide")

# CSS pour le logo et le style global
css_logo = """
<style>
    .header-logo {
        position: absolute;
        top: 10px;
        right: 20px;
        z-index: 9999;
        font-family: 'Arial Black', Impact, sans-serif;
        font-size: 32px;
        text-shadow: 
            -3px -3px 0 #FFF,  
             3px -3px 0 #FFF,
            -3px  3px 0 #FFF,
             3px  3px 0 #FFF,
             0px  4px 5px rgba(0,0,0,0.2); 
    }
    .text-cherche { color: white; }
    .text-logement { color: #FF8C00; }
    .block-container { padding-top: 4rem; }
</style>
<div class="header-logo">
    <span class="text-cherche">cherche ton</span> <span class="text-logement">logement</span>
</div>
"""
st.markdown(css_logo, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CONNEXION À DUCKDB ET RÉCUPÉRATION DYNAMIQUE
# -----------------------------------------------------------------------------
@st.cache_data
def get_geodata(dept_code):
    """
    Récupère 100% des communes, mais uniquement pour le département sélectionné.
    """
    try:
        con = duckdb.connect("immo_bi_database.db", read_only=True)
        con.execute("INSTALL spatial;")
        con.execute("LOAD spatial;")
        
        # On filtre via le code INSEE (ex: les codes du Morbihan commencent par '56')
        # On a retiré le "LIMIT 100" !
        query = f"""
            SELECT nom, ST_AsGeoJSON(geom), code 
            FROM dim_geographie 
            WHERE geom IS NOT NULL
            AND code LIKE '{dept_code}%'
        """
        result = con.execute(query).fetchall()
        
        features = []
        for row in result:
            if row[1] is not None:
                geometry = json.loads(row[1])
                features.append({
                    "type": "Feature",
                    "properties": {
                        "nom": row[0],
                        "code": row[2],
                        "prix_m2": 2500 # Donnée fictive en attendant la jointure DVF
                    },
                    "geometry": geometry
                })
                
        con.close()
        
        # Petit calcul pour centrer la carte approximativement sur le département
        # On prend le premier polygone trouvé s'il existe
        center_lat, center_lon = 46.603354, 1.888334 # Centre France par défaut
        if features and features[0]["geometry"]["type"] == "Polygon":
            first_coord = features[0]["geometry"]["coordinates"][0][0]
            center_lon, center_lat = first_coord[0], first_coord[1]
            
        return {
            "geojson": {"type": "FeatureCollection", "features": features},
            "center": [center_lat, center_lon],
            "count": len(features)
        }
    except Exception as e:
        return f"Erreur détaillée : {str(e)}"

# -----------------------------------------------------------------------------
# INTERFACE UTILISATEUR
# -----------------------------------------------------------------------------

st.title("🏡 Analyse Immobilière Territoriale")
st.markdown("Découvrez les prix de l'immobilier en croisant la base DVF, l'Insee et les données environnementales.")

st.divider()

tab1, tab2 = st.tabs(["🗺️ Carte Analytique (Interactive)", "📍 Visualisateur Officiel IGN"])

with tab1:
    # --- NOUVEAU : Filtre par département ---
    col_filtre, col_vide = st.columns([1, 2])
    with col_filtre:
        departements = {
            "56": "Morbihan (56)",
            "44": "Loire-Atlantique (44)",
            "35": "Ille-et-Vilaine (35)",
            "75": "Paris (75)"
        }
        dept_choisi = st.selectbox("Choisissez un département à analyser :", options=list(departements.keys()), format_func=lambda x: departements[x])
    
    st.write(f"👉 **Survolez et cliquez sur un contour géographique** du {departements[dept_choisi]} pour voir ses statistiques détaillées.")

    with st.spinner(f"Chargement des {departements[dept_choisi]} depuis DuckDB..."):
        geo_result = get_geodata(dept_choisi)

    if isinstance(geo_result, dict):
        # Création de la carte centrée sur le département choisi
        m = folium.Map(location=geo_result["center"], zoom_start=9, tiles="CartoDB positron")
        
        folium.GeoJson(
            geo_result["geojson"],
            name="Limites Administratives",
            style_function=lambda feature: {
                'fillColor': '#3498db',
                'color': '#2c3e50',
                'weight': 1,
                'fillOpacity': 0.3,
            },
            highlight_function=lambda feature: {
                'fillOpacity': 0.7,
                'weight': 3,
                'fillColor': '#FF8C00'
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['nom', 'code'],
                aliases=['Commune:', 'Code INSEE:'],
                localize=True
            )
        ).add_to(m)
        
        map_col, details_col = st.columns([2, 1])
        
        with map_col:
            map_data = st_folium(m, width=700, height=500, returned_objects=["last_active_drawing"])
            
        with details_col:
            st.subheader("📍 Focus Zone")
            st.metric("Communes chargées", f"{geo_result['count']} polygones")
            st.markdown("---")
            
            if map_data.get("last_active_drawing"):
                props = map_data["last_active_drawing"]["properties"]
                
                st.success(f"**{props['nom']}** (Code INSEE: {props['code']})")
                st.markdown(f"### {props['prix_m2']} €/m²")
                st.caption("Données en cours d'intégration depuis DuckDB...")
                
                st.button(f"Lancer l'analyse complète de {props['nom']}", type="primary", use_container_width=True)
                
            else:
                st.info("👈 Cliquez sur un contour pour afficher les statistiques.")
    else:
        st.warning("Impossible de charger les bordures géographiques. Vérifiez votre base DuckDB.")
        st.error(geo_result)

with tab2:
    st.subheader("Atlas Officiel Admin Express (Source: Géoportail)")
    st.write("Ce visualisateur utilise le Web Component officiel de l'IGN. Il est indépendant de notre base de données de prix.")
    
    code_ign = """
    <div style="height: 600px; width: 100%;">
        <script src="https://cdn.jsdelivr.net/gh/geonetwork/geonetwork-ui@wc-dist-main/gn-wc.js"></script>
        <gn-dataset-view-map
                api-url="https://data.geopf.fr/catalog"
                dataset-id="IGNF_ADMIN-EXPRESS"
                primary-color="#0f4395"
                secondary-color="#8bc832"
                main-color="#555"
                background-color="#fdfbff"
                main-font="'Inter', sans-serif"
                title-font="'DM Serif Display', serif"
                style="display: block; width: 100%; height: 100%;"
        ></gn-dataset-view-map>
    </div>
    """
    components.html(code_ign, height=650)