import streamlit as st
import folium
from streamlit_folium import st_folium
import os
from PIL import Image

# 1. Configuration de la page
st.set_page_config(page_title="Cherche Ton Logement", page_icon="📍", layout="wide")

# 2. Chargement sécurisé du logo
# Cette ligne trouve automatiquement le logo s'il est dans le même dossier que ce script
chemin_logo = os.path.join(os.path.dirname(__file__), "logo.png")
logo = Image.open(chemin_logo)

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
    
    # On centre le logo avec des colonnes
    col1, col_logo, col3 = st.columns([1, 2, 1])
    with col_logo:
        # On affiche l'image centrée
        st.image(logo, use_container_width=True)
    
    st.write("") # Espace
    
    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        st.markdown("<h3 style='text-align: center;'>Comment souhaitez-vous chercher ?</h3>", unsafe_allow_html=True)
        st.write("")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Exploratoire (Carte interactive)", use_container_width=True, type="primary"):
                naviguer_vers("exploratoire")
        with col_btn2:
            if st.button("Recherche précise (Recommandation)", use_container_width=True):
                naviguer_vers("recherche")

# ==========================================
# PAGE 2 : MODE EXPLORATOIRE
# ==========================================
elif st.session_state.page == "exploratoire":
    
    # Bouton retour en haut à gauche
    if st.button(" Retour à l'accueil"):
        naviguer_vers("accueil")
        
    # Séparation de l'écran : 70% pour la carte, 30% pour les critères
    col_carte, col_criteres = st.columns([7, 3])
    
    with col_carte:
        st.title("Mode Exploratoire")
        # Carte fictive 
        m = folium.Map(location=[46.2276, 2.2137], zoom_start=5)
        st_folium(m, width=800, height=600)
        
    with col_criteres:
        # On place le logo en haut à droite (au-dessus des filtres, comme sur votre maquette)
        col_vide, col_img = st.columns([1, 2])
        with col_img:
            st.image(logo, use_container_width=True)
            
        st.subheader("Vos Critères")
        ville = st.selectbox("Ville", ["Sélectionnez...", "Vannes", "Lorient", "Rennes"])
        prix = st.slider("Prix Max (€/m²)", 1000, 10000, 3000)
        bruit = st.selectbox("Bruit (PEB)", ["Peu importe", "Zone Calme", "Zone Bruyante"])
        energie = st.multiselect("Énergie (DPE)", ["A", "B", "C", "D", "E", "F", "G"])

# ==========================================
# PAGE 3 : RECHERCHE PRÉCISE
# ==========================================
elif st.session_state.page == "recherche":
    
    col_titre, col_img_droite = st.columns([8, 2])
    with col_titre:
        if st.button(" Retour à l'accueil"):
            naviguer_vers("accueil")
        st.title("Recherche Précise")
        st.write("Dites-nous ce que vous cherchez, nous vous dirons où habiter !")
    with col_img_droite:
        st.image(logo, use_container_width=True)
    
    with st.form("formulaire_recherche"):
        budget = st.number_input("Budget Total (€)", min_value=50000, step=10000)
        surface_min = st.number_input("Surface minimum (m²)", min_value=9, step=5)
        importance_calme = st.slider("Importance du calme (1=Faible, 5=Indispensable)", 1, 5, 3)
        
        soumis = st.form_submit_button("Trouver mon secteur idéal", type="primary")
        
        if soumis:
            st.success("L'algorithme a trouvé 3 secteurs parfaits pour vous !")