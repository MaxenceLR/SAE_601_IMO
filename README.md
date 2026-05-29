# Real Estate Business Intelligence Tool

> **Core Question:** Given a price, a location, and a set of property characteristics, is this a good deal?

##  À propos du projet

L'objectif de ce projet est de concevoir et de développer un outil complet de **Business Intelligence (BI)** destiné aux acheteurs, vendeurs et professionnels de l'immobilier. Cet outil permet de répondre à une question centrale : **ce bien immobilier est-il affiché au juste prix ?**

Pour y parvenir, l'application collecte, nettoie, croise et expose des données provenant de multiples sources publiques. Cela permet d'obtenir une évaluation précise en combinant l'historique des transactions, les critères environnementaux et le contexte socio-économique.

---

## Sources de données intégrées

Pour évaluer la pertinence du prix d'un bien, le projet croise plusieurs dimensions de données publiques :

*   **Historique des transactions :** Analyse des ventes passées sur le secteur pour comprendre l'évolution du marché immobilier local.
*   **Performance énergétique :** Prise en compte du DPE (Diagnostic de Performance Énergétique) pour évaluer l'impact écologique et financier.
*   **Exposition au bruit :** Cartographie et indices de nuisances sonores environnantes.
*   **Contexte socio-économique :** Indicateurs sur le quartier (revenus moyens, attractivité, démographie).
*   **Informations géographiques :** Proximité des services, transports, écoles et points d'intérêt.

---

##  Architecture et Objectifs Techniques

Le projet respecte le cycle de vie classique d'un projet de données (Pipeline ETL) :

1.  **Collecte (Extract) :** Récupération des données via des API publiques et des fichiers open-data.
2.  **Nettoyage & Traitement (Transform) :** Filtrage, gestion des valeurs manquantes, normalisation et géocodage des données.
3.  **Croisement (Load) :** Stockage et structuration des données pour permettre des requêtes croisées fluides.
4.  **Exposition (Restitution) :** Interface ou tableau de bord permettant d'entrer les caractéristiques d'un bien et d'obtenir son analyse de valeur.

---

##  Installation et Utilisation

*pip isntalle requirements.txt
 python data/src/Lancement_script.py*


### Clonage du projet
```bash
git clone //partage-ens.univ-ubs.fr/projets/3bvi11/Projet_imo (pas toucher pls)