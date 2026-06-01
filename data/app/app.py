import streamlit as st
import folium
from streamlit_folium import st_folium
import os
from PIL import Image

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
    
    with col_carte:
        st.title("Exploration Territoriale")
        # Carte fictive centrée sur Nantes (Département 44)
        m = folium.Map(location=[47.2184, -1.5536], zoom_start=11)
        st_folium(m, width=800, height=600)
        
    with col_criteres:
        st.subheader("Filtres de recherche")
        # Ces valeurs statiques seront remplacées plus tard par des appels au Back-End
        ville = st.selectbox("Secteur / Commune", ["Secteur Ouest", "Secteur Est", "Nantes Centre", "Saint-Herblain"])
        prix = st.slider("Prix Max (€/m²)", 1000, 10000, 4500)
        bruit = st.selectbox("Environnement (PEB)", ["Indifférent", "Hors zone de bruit", "Zone modérée"])
        energie = st.multiselect("Performance Énergétique (DPE)", ["A", "B", "C", "D", "E", "F", "G"], default=["A", "B", "C"])

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
            st.success("Analyse terminée !")
            st.info("💡 **Exemple de recommandation générée par l'algorithme :**\n\nDans le quartier de **Chantenay**, les biens classés G s'achètent à 2500€/m². Avec vos travaux estimés à 1000€/m², votre coût de revient est de 3500€/m². Un bien classé C se revendant à 4200€/m² dans ce secteur, **votre profit potentiel est de 700€/m²**.")
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
        variable_x = st.selectbox("Comparer selon :", ["Commune", "Étiquette DPE", "Année de construction"])
    with col_f2:
        variable_y = st.selectbox("Indicateur :", ["Prix moyen au m²", "Volume de ventes", "Surface moyenne"])
        
    st.divider()
    
    # Espace réservé pour les futurs graphiques (Streamlit ou Plotly)
    st.markdown(f"*(Ici apparaîtra le graphique croisant **{variable_x}** et **{variable_y}** via le Back-End)*")
    st.bar_chart({"Données fictives A": [10, 20, 30], "Données fictives B": [15, 25, 35]})