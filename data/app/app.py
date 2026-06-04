import streamlit as st
import folium
from streamlit_folium import st_folium
import os
from PIL import Image
import backend 
import altair as alt
import branca.colormap as cm

# 1. Configuration de la page
st.set_page_config(page_title="Invest'Immo BI", page_icon="🏢", layout="wide")

# 2. Chargement sécurisé du logo
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
            if st.button("Mode Exploratoire\n(Carte Interactive)", use_container_width=True):
                naviguer_vers("exploratoire")
        with col_btn2:
            if st.button("Investissement\n(Stratégie Rénovation)", use_container_width=True, type="primary"):
                naviguer_vers("recherche")
        with col_btn3:
            if st.button("Analyse du Marché\n(Graphiques & Tendances)", use_container_width=True):
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
        liste_villes = backend.get_villes()
        ville = st.selectbox("Secteur / Commune", liste_villes)
        
        prix = st.slider("Prix Max (€/m²)", 1000, 10000, 4500)
        bruit = st.selectbox("Environnement (PEB)", ["Indifférent", "Hors zone de bruit", "Zone modérée"])
        energie = st.multiselect("Performance Énergétique (DPE)", ["A", "B", "C", "D", "E", "F", "G"], default=["A", "B", "C"])

    with col_carte:
        st.title("Exploration Territoriale")
        
        df_biens = backend.get_donnees_carte(ville, prix, bruit, energie)
        
        if df_biens.empty:
            if ville == "Sélectionnez une ville...":
                st.info("👈 Veuillez sélectionner une ville dans le menu de droite.")
            else:
                st.warning("Aucun bien ne correspond à vos critères.")
        else:
            lat_moyenne = df_biens['latitude'].mean()
            lon_moyenne = df_biens['longitude'].mean()
            m = folium.Map(location=[lat_moyenne, lon_moyenne], zoom_start=13)
            
            # --- ÉTAPE A : Dessiner les "Quartiers" (Zones de 1km²) ---
            # On groupe les données par secteur pour calculer les stats de la zone
            secteurs = df_biens.groupby(['secteur_lat', 'secteur_lon']).agg(
                prix_moyen=('prix_m2', 'mean'),
                nb_biens=('prix_m2', 'count')
            ).reset_index()

            for _, zone in secteurs.iterrows():
                z_lat = zone['secteur_lat']
                z_lon = zone['secteur_lon']
                
                # Mathématiques magiques : Un arrondi à 0.01 degré correspond à un carré 
                # allant de -0.005 à +0.005 autour du point central.
                limites_carre = [
                    [z_lat - 0.005, z_lon - 0.005], # Coin sud-ouest
                    [z_lat + 0.005, z_lon + 0.005]  # Coin nord-est
                ]
                
                texte_zone = f"<b>Zone de Quartier</b><br>Prix moyen : {zone['prix_moyen']:,.0f} €/m²<br>Biens dispo : {zone['nb_biens']}"
                
                folium.Rectangle(
                    bounds=limites_carre,
                    color="#4A90E2",         # Couleur de la bordure
                    weight=1,                # Bordure très fine
                    fill=True,
                    fill_color="#4A90E2",    # Couleur du fond
                    fill_opacity=0.15,       # Assez transparent (15%)
                    tooltip=texte_zone       # Affichage au survol de la souris
                ).add_to(m)

            # --- ÉTAPE B : Dessiner les points individuels (Dégradé de prix) ---
            
            # 1. Calcul du prix min et max de la ville actuelle pour calibrer le dégradé
            min_prix = df_biens['prix_m2'].min()
            max_prix = df_biens['prix_m2'].max()
            
            # Sécurité au cas où il n'y aurait qu'un seul bien (évite un crash mathématique)
            if min_prix == max_prix:
                min_prix = min_prix - 1
                max_prix = max_prix + 1
            
            # 2. Création de l'échelle de couleurs (Vert = moins cher, Jaune = moyen, Rouge = cher)
            colormap = cm.LinearColormap(
                colors=['#00b894', '#fdcb6e', '#d63031'], # Vert menthe, Jaune soleil, Rouge vif
                vmin=min_prix, 
                vmax=max_prix
            )
            colormap.caption = f"Échelle des prix au m² à {ville} (€)"
            m.add_child(colormap) # Ajoute la légende sur la carte

            # 3. Placement des points avec leur nouvelle couleur
            for idx, row in df_biens.iterrows():
                texte_dpe = f"DPE : {row['etiquette_dpe']}"
                popup_text = f"<b>Prix: {row['prix_m2']:,.0f} €/m²</b><br>{texte_dpe}<br>Bruit: {row['peb_zone']}"
                
                # On détermine la couleur exacte de ce bien grâce à l'échelle
                couleur_bien = colormap(row['prix_m2'])
                
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=6, # On grossit légèrement le point pour mieux voir la couleur
                    color="#333333", # Une petite bordure gris foncé pour le faire ressortir sur le fond bleu
                    weight=1.5,
                    fill=True,
                    fill_color=couleur_bien,
                    fill_opacity=0.95,
                    popup=folium.Popup(popup_text, max_width=200)
                ).add_to(m)
                
            st_folium(m, use_container_width=True, height=700, returned_objects=[])
            st.caption(f"📍 {len(df_biens)} biens affichés, répartis sur {len(secteurs)} zones (quartiers).")

            
# ==========================================
# PAGE 3 : INVESTISSEMENT (ACHAT & RÉNOVATION)
# ==========================================
elif st.session_state.page == "recherche":
    
    if st.button("🔙 Retour à l'accueil"):
        naviguer_vers("accueil")
        
    st.title("Stratégies d'Investissement")
    
    tab_achat, tab_renov = st.tabs(["🏡 Achat Stratégique", "🛠️ Achat & Rénovation (Déficit Foncier)"])
    
   # --- ONGLET 1 : ACHAT STRATÉGIQUE ---
    with tab_achat:
        st.write("Trouvez les meilleurs secteurs selon votre profil d'investisseur (Patrimonial vs Rendement).")
        
        col_criteres_a, col_carte_a = st.columns([1, 2])
        with col_criteres_a:
            with st.form("form_achat"):
                st.subheader("Budget & Critères")
                budget_max = st.number_input("Budget Max (€)", min_value=50000, step=10000, value=250000)
                surface_min = st.number_input("Surface minimum (m²)", min_value=9, step=5, value=50)
                energie = st.multiselect("DPE Accepté", ["A", "B", "C", "D"], default=["C", "D"])
                
                st.divider()
                st.subheader("Profil Investisseur")
                # NOUVEAU : Choix de la stratégie
                strategie = st.radio("Objectif visé :", [
                    "🏛️ Patrimonial (Secteurs prisés, risque faible)", 
                    "💰 Rendement (Prix bas, forte marge)",
                    "⚖️ Équilibré (Compromis)"
                ])
                # NOUVEAU : Filtre Littoral
                choix_littoral = st.selectbox("Préférence géographique :", ["Indifférent", "🌊 Littoral uniquement", "🌳 Terres / Rétro-littoral"])
                
                soumis_achat = st.form_submit_button("Trouver la perle rare", type="primary")
        
        with col_carte_a:
            if soumis_achat:
                # On envoie les nouveaux critères au backend
                df_achat = backend.get_recommandations_achat(budget_max, surface_min, energie, strategie, choix_littoral)
                
                if df_achat.empty:
                    st.warning("Aucune ville ne correspond à ces critères si stricts. Essayez d'augmenter le budget ou d'élargir le secteur.")
                else:
                    st.success("Analyse réussie ! Voici les secteurs qui matchent avec votre profil :")
                    
                    m_achat = folium.Map(location=[df_achat['lat'].mean(), df_achat['lon'].mean()], zoom_start=9)
                    
                    # On adapte les couleurs : or pour le patrimonial, vert pour le rendement
                    couleurs = {"Patrimonial": "gold", "Rendement": "green", "Équilibré": "blue", "À Fuir (Hors Budget)": "red"}
                    
                    for _, row in df_achat.iterrows():
                        cat = row['categorie']
                        texte = f"<b>{row['nom_commune']}</b><br>Profil: {cat}<br>Prix: {row['prix_moyen_m2']} €/m²<br>Budget estimé: {row['budget_estime']} €"
                        
                        folium.Marker(
                            location=[row['lat'], row['lon']],
                            popup=folium.Popup(texte, max_width=250),
                            icon=folium.Icon(color=couleurs.get(cat, "gray"), icon="star" if cat == "Patrimonial" else "euro", prefix='fa'),
                            tooltip=row['nom_commune']
                        ).add_to(m_achat)
                    
                    st_folium(m_achat, use_container_width=True, height=500, returned_objects=[])

    # --- ONGLET 2 : RÉNOVATION ---
    with tab_renov:
        st.write("Identifiez les passoires thermiques à rénover pour maximiser la plus-value au mètre carré.")
        
        col_form_r, col_result_r = st.columns([1, 1])
        with col_form_r:
            with st.form("form_renov"):
                st.subheader("Critères financiers")
                budget_total = st.number_input("Budget Total Actuel (€)", min_value=50000, step=10000, value=200000)
                surface_visee = st.number_input("Surface visée (m²)", min_value=9, step=5, value=40)
                
                st.divider()
                st.subheader("Projet Rénovation")
                bruit_renov = st.selectbox("Environnement (PEB)", ["Indifférent", "Hors zone de bruit", "Zone modérée"], key="bruit2")
                cout_renovation = st.slider("Coût des travaux (€/m²)", 500, 2000, 1000, step=100)
                cible_dpe = st.selectbox("Étiquette DPE visée", ["A", "B", "C", "D"], index=2)
                
                soumis_renov = st.form_submit_button("Calculer la rentabilité", type="primary")

        with col_result_r:
            if soumis_renov:
                df_invest = backend.get_opportunites_renovation(budget_total, surface_visee, cout_renovation, cible_dpe, bruit_renov)
                
                if df_invest.empty:
                    st.warning("Aucun secteur rentable avec ces critères.")
                else:
                    st.success("Top 5 des zones pour la rénovation :")
                    
                    # 1. Affichage du tableau (On cache les colonnes GPS avec drop)
                    st.dataframe(
                        df_invest.drop(columns=['secteur_lat', 'secteur_lon']).rename(columns={
                            "nom_commune": "Secteur",
                            "prix_achat_m2": "Achat Passoire (€/m²)",
                            "prix_revente_m2": f"Revente DPE {cible_dpe} (€/m²)",
                            "profit_m2_estime": "Gain net estimé (€/m²)"
                        }),
                        use_container_width=True, hide_index=True
                    )

                    # 2. Affichage de la carte des opportunités
                    st.write("### 🗺️ Carte des opportunités")
                    
                    # On centre la carte sur la meilleure opportunité (la première ligne du tableau)
                    meilleure_lat = df_invest.iloc[0]['secteur_lat']
                    meilleure_lon = df_invest.iloc[0]['secteur_lon']
                    m_renov = folium.Map(location=[meilleure_lat, meilleure_lon], zoom_start=10)
                    
                    # On dessine un cercle ou un carré pour chaque zone du Top 5
                    for idx, row in df_invest.iterrows():
                        # On met en valeur la zone n°1 (la plus rentable) avec une couleur différente
                        couleur = "gold" if idx == 0 else "blue"
                        texte_popup = f"<b>{row['nom_commune']}</b><br>Gain estimé : +{row['profit_m2_estime']:,.0f} €/m²<br>Achat : {row['prix_achat_m2']:,.0f} €/m²<br>Revente : {row['prix_revente_m2']:,.0f} €/m²"
                        
                        folium.CircleMarker(
                            location=[row['secteur_lat'], row['secteur_lon']],
                            radius=15, # Un rond assez grand pour représenter le quartier
                            color=couleur,
                            fill=True,
                            fill_color=couleur,
                            fill_opacity=0.4,
                            tooltip=f"Gagnez {row['profit_m2_estime']} €/m² ici !",
                            popup=folium.Popup(texte_popup, max_width=250)
                        ).add_to(m_renov)
                        
                        # Ajout d'une petite icône au centre de la zone
                        folium.Marker(
                            location=[row['secteur_lat'], row['secteur_lon']],
                            icon=folium.Icon(color="green" if idx == 0 else "blue", icon="wrench", prefix="fa")
                        ).add_to(m_renov)
                    
                    st_folium(m_renov, use_container_width=True, height=400, returned_objects=[])
# ==========================================
# PAGE 4 : DATAVIZ (GRAPHIQUES)
# ==========================================
elif st.session_state.page == "dataviz":
    
    if st.button("🔙 Retour à l'accueil"):
        naviguer_vers("accueil")
        
    st.title("Analyse du Marché Immobilier")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        variable_x = st.selectbox("Analyser la répartition par :", ["Commune", "Étiquette DPE", "Année de construction"])
    with col_f2:
        variable_y = st.selectbox("Indicateur à calculer :", ["Volume de ventes", "Prix moyen au m²", "Surface moyenne"])
        
    st.divider()
    
    df_graph = backend.get_donnees_graphiques(variable_x, variable_y)
    
    if df_graph.empty:
        st.warning("Aucune donnée disponible pour ce croisement.")
    else:
        # --- NOUVEAUTÉ : Les cartes du TOP 3 ---
        st.subheader(f"🏆 Top 3 - {variable_y}")
        col_m1, col_m2, col_m3 = st.columns(3)
        colonnes_metrics = [col_m1, col_m2, col_m3]
        
        # Définition de l'unité à afficher sur la carte selon le choix de l'utilisateur
        unite = " €/m²" if "Prix" in variable_y else (" m²" if "Surface" in variable_y else "")
        
        # On boucle sur les 3 premières lignes (ou moins s'il y a moins de 3 résultats)
        top_n = min(3, len(df_graph))
        for i in range(top_n):
            with colonnes_metrics[i]:
                nom = df_graph.iloc[i][variable_x]
                valeur = df_graph.iloc[i][variable_y]
                # st.metric crée automatiquement le joli bloc avec le grand chiffre
                st.metric(label=str(nom), value=f"{valeur:,.0f}{unite}".replace(',', ' '))

        st.divider()
        
        # --- LE GRAPHIQUE ---
        st.subheader(f"{variable_y} en fonction de : {variable_x} (Top 50)")
        
        # On utilise Altair pour forcer le tri décroissant (sort='-y')
        graphique = alt.Chart(df_graph).mark_bar().encode(
            x=alt.X(f"{variable_x}:N", sort='-y', title=variable_x),
            y=alt.Y(f"{variable_y}:Q", title=variable_y),
            tooltip=[variable_x, variable_y] # Petit bonus : affiche les valeurs au survol de la souris !
        )
        
        st.altair_chart(graphique, use_container_width=True)
        
        with st.expander("Voir les données brutes"):
            st.dataframe(df_graph, use_container_width=True)