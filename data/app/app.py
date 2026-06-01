import streamlit as st
import folium
from streamlit_folium import st_folium
import os
from PIL import Image
import backend # On importe notre nouveau fichier

# 1. Configuration de la page
st.set_page_config(page_title="Invest'Immo BI", page_icon="🏢", layout="wide")

# 2. Chargement sécurisé du logo (assurez-vous d'avoir un logo.png dans le même dossier)
try:
    chemin_logo = os.path.join(os.path.dirname(__file__), "logo.png")
    logo = Image.open(chemin_logo)
    has_logo = True
except FileNotFoundError:
    has_logo = False

# --- GESTION DE LA NAVIGATION ---
if "page" not in st.session_state:
    st.session_state.page = "accueil"

def naviguer_vers(page_nom):
    st.session_state.page = page_nom
    st.rerun()

# ==========================================
# PAGE 1 : ACCUEIL
# ==========================================
if st.session_state.page == "accueil":
    
    col1, col_logo, col3 = st.columns([1, 2, 1])
    with col_logo:
        if has_logo:
            st.image(logo, use_container_width=True)
        else:
            st.markdown("<h1 style='text-align: center;'>🏢 Invest'Immo</h1>", unsafe_allow_html=True)
    
    st.write("") 
    
    _, col_center, _ = st.columns([1, 4, 1])
    with col_center:
        st.markdown("<h3 style='text-align: center;'>Que souhaitez-vous faire aujourd'hui ?</h3>", unsafe_allow_html=True)
        st.write("")
        
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("🗺️ Mode Exploratoire\n(Carte Interactive)", use_container_width=True):
                naviguer_vers("exploratoire")
        with col_btn2:
            if st.button("💡 Investissement\n(Stratégie Rénovation)", use_container_width=True, type="primary"):
                naviguer_vers("recherche")
        with col_btn3:
            if st.button("📊 Analyse du Marché\n(Graphiques & Tendances)", use_container_width=True):
                naviguer_vers("dataviz")


# ==========================================
# PAGE 2 : MODE EXPLORATOIRE (CARTE)
# ==========================================
elif st.session_state.page == "exploratoire":
    
    if st.button("🔙 Retour à l'accueil"):
        naviguer_vers("accueil")
        
    col_carte, col_criteres = st.columns([7, 3])
    
    with col_criteres:
        st.subheader("Filtres de recherche")
        
        # --- APPEL AU BACKEND : Liste dynamique des villes ---
        liste_villes = backend.get_villes()
        ville = st.selectbox("Secteur / Commune", liste_villes)
        
        prix = st.slider("Prix Max (€/m²)", 1000, 10000, 4500)
        bruit = st.selectbox("Environnement (PEB)", ["Indifférent", "Hors zone de bruit", "Zone modérée"])
        energie = st.multiselect("Performance Énergétique (DPE)", ["A", "B", "C", "D", "E", "F", "G"], default=["A", "B", "C"])

    with col_carte:
        st.title("Exploration Territoriale")
        
        # --- APPEL AU BACKEND : Récupération des données ---
        df_biens = backend.get_donnees_carte(ville, prix, bruit, energie)
        
        if df_biens.empty:
            if ville == "Sélectionnez une ville...":
                st.info("👈 Veuillez sélectionner une ville dans le menu de droite.")
            else:
                st.warning("Aucun bien ne correspond à vos critères.")
        else:
            # On centre la carte sur le premier point trouvé
            lat_moyenne = df_biens['latitude'].mean()
            lon_moyenne = df_biens['longitude'].mean()
            m = folium.Map(location=[lat_moyenne, lon_moyenne], zoom_start=12)
            
            # On place un marqueur pour chaque bien
            for idx, row in df_biens.iterrows():
                popup_text = f"Prix: {row['prix_m2']} €/m²<br>DPE: {row['etiquette_dpe']}<br>Bruit: {row['peb_zone']}"
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=5,
                    color="blue" if row['etiquette_dpe'] in ['A', 'B', 'C'] else "red",
                    fill=True,
                    popup=folium.Popup(popup_text, max_width=200)
                ).add_to(m)
                
            st_folium(m, width=800, height=600)
            st.caption(f"📍 {len(df_biens)} biens affichés sur la carte.")
# ==========================================
# PAGE 3 : INVESTISSEMENT & RÉNOVATION
# ==========================================
elif st.session_state.page == "recherche":
    
    if st.button("🔙 Retour à l'accueil"):
        naviguer_vers("accueil")
        
    st.title("Stratégie d'Investissement & Rénovation")
    st.write("Identifiez les secteurs où l'achat d'une passoire thermique et sa rénovation génèrent le plus de plus-value.")
    
    col_form, col_result = st.columns([1, 1])
    
    with col_form:
        with st.form("formulaire_investissement"):
            st.subheader("Vos critères d'achat")
            budget = st.number_input("Budget Total Actuel (€)", min_value=50000, step=10000, value=200000)
            surface_min = st.number_input("Surface minimum visée (m²)", min_value=9, step=5, value=40)
            
            st.divider()
            st.subheader("Hypothèses de travaux")
            cout_renovation = st.slider("Coût estimé des travaux (€/m²)", 500, 2000, 1000, step=100)
            cible_dpe = st.selectbox("Étiquette DPE visée après travaux", ["A", "B", "C", "D"], index=2) # "C" par défaut
            
            soumis = st.form_submit_button("Calculer la rentabilité par secteur", type="primary")

    with col_result:
        if soumis:
            st.success("Analyse terminée ! Voici les meilleures opportunités :")
            
            # --- APPEL AU BACKEND ---
            df_invest = backend.get_opportunites_investissement(budget, surface_min, cout_renovation, cible_dpe)
            
            if df_invest.empty:
                st.warning("Aucun secteur ne permet de réaliser une plus-value avec ces critères. Essayez d'augmenter votre budget ou de réduire le coût des travaux.")
            else:
                st.write("### Top 5 des secteurs rentables")
                st.dataframe(
                    df_invest.rename(columns={
                        "nom_commune": "Secteur",
                        "prix_achat_m2": "Achat (Passoire) €/m²",
                        "prix_revente_m2": f"Revente (DPE {cible_dpe}) €/m²",
                        "profit_m2_estime": "Plus-value estimée €/m²"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
                
                # Petit calcul de mise en situation avec la meilleure ville
                meilleure_ville = df_invest.iloc[0]
                profit_total = meilleure_ville['profit_m2_estime'] * surface_min
                st.info(f"💡 **Conseil de l'algorithme :**\n\nEn achetant un bien de **{surface_min}m²** à **{meilleure_ville['nom_commune']}**, et après avoir payé vos travaux, vous pourriez générer une plus-value nette estimée à **{profit_total:,.0f} €** à la revente !")
        else:
            st.write("Remplissez le formulaire pour découvrir les opportunités de déficit foncier et de plus-value.")
# ==========================================
# PAGE 4 : DATAVIZ (GRAPHIQUES)
# ==========================================
elif st.session_state.page == "dataviz":
    
    if st.button("🔙 Retour à l'accueil"):
        naviguer_vers("accueil")
        
    st.title("Analyse du Marché Immobilier")
    
    # Filtres horizontaux pour les graphiques
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        variable_x = st.selectbox("Analyser la répartition par :", ["Étiquette DPE", "Commune", "Année de construction"])
    with col_f2:
        variable_y = st.selectbox("Indicateur à calculer :", ["Prix moyen au m²", "Volume de ventes", "Surface moyenne"])
        
    st.divider()
    
    # --- APPEL AU BACKEND ---
    df_graph = backend.get_donnees_graphiques(variable_x, variable_y)
    
    if df_graph.empty:
        st.warning("Aucune donnée disponible pour ce croisement.")
    else:
        st.subheader(f"{variable_y} en fonction de : {variable_x}")
        
        # Streamlit crée automatiquement un superbe graphique interactif !
        st.bar_chart(
            data=df_graph, 
            x=variable_x, 
            y=variable_y,
            use_container_width=True
        )
        
        # Optionnel : afficher le tableau de données en dessous pour les plus curieux
        with st.expander("Voir les données brutes"):
            st.dataframe(df_graph, use_container_width=True)