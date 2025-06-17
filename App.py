import streamlit as st
import pandas as pd
import folium
from geopy.distance import geodesic
from streamlit_folium import st_folium
from Modules.modules import convert_to_polygon
import ast


st.set_page_config(page_title="Sites Complexes", layout="wide")

# Chargement des données depuis un fichier CSV avec cache
@st.cache_data
def load_data():
    df = pd.read_csv('centres_avec_boutiques_vertes.csv')
    df_imb = pd.read_csv("export_en_gps_clean.csv")
    df_canopee = pd.read_excel("Communes_notifiees_fev_25_V1 (1).xlsx")
    return df, df_imb, df_canopee

# Charger les données
df, df_imb, df_canopee = load_data()


# Convertir la colonne 'imbs' de chaînes de caractères en listes de listes
df['imbs'] = df['imbs'].apply(lambda x: ast.literal_eval(x) if not pd.isna(x) else None)



# Titre de l'application
st.title("Sites Complexes")

# # Sélecteur de centre commercial
# options = [''] + df['nom'].tolist()
# selected_commercial = st.sidebar.selectbox("Sélectionnez un centre commercial", options)

with st.sidebar:
    st.image("images/logo_807.png", width=90)  

# --- Choix du type de filtre ---
filter_type = st.sidebar.radio("Filtrer par", ["Centre", "Boutique", "Foncière", "Région"])


selected_commercial = None
selected_enseigne = None
selected_gestionnaire = None
selected_region = None

if filter_type == "Centre":
    options = [''] + sorted(df['nom'].dropna().unique().tolist())
    selected_commercial = st.sidebar.selectbox("Sélectionnez un centre commercial", options)

elif filter_type == "Boutique":
    # Extraction de toutes les enseignes possibles
    all_enseignes = df['enseignes'].dropna().str.split(r" \| ").explode().str.strip().unique()
    enseigne_options = [''] + sorted(all_enseignes)
    selected_enseigne = st.sidebar.selectbox("Sélectionnez une enseigne", enseigne_options)

elif filter_type == "Foncière":
    foncieres = df['gestionnaires'].dropna().unique()
    foncieres_sorted = [''] + sorted(foncieres)
    selected_gestionnaire = st.sidebar.selectbox("Sélectionnez une foncière", foncieres_sorted)
 
elif filter_type == "Région":
    regions = df['region'].dropna().unique()
    regions_sorted = [''] + sorted(regions)
    selected_region = st.sidebar.selectbox("Sélectionnez une région", regions_sorted)
    
     
# Vérification si un centre commercial est sélectionné
if selected_commercial:
    
    selected_data = df[df['nom'] == selected_commercial].iloc[0]
    m = folium.Map(location=[selected_data['latitude'], selected_data['longitude']], zoom_start=16)
    
    # Infos clés pour l'infobulle
    adresse_parts = [selected_data.get(f"adresse{i}") for i in range(1, 4) if not pd.isna(selected_data.get(f"adresse{i}"))]
    adresse_complete = ", ".join(adresse_parts)
    ville = selected_data.get("nom_ville", "")
    code_postal = selected_data.get("code_postal", "")
    anciennete = selected_data.get("nb_annees_ouverture", "N/A")
    nb_boutiques = selected_data.get("nb_boutiques", "N/A")
    type_cc = selected_data.get("typologie_cc_long", "")
    proprietaire = selected_data.get("gestionnaires", "N/A")
    superficie = selected_data.get("surface_gla", "N/A")

    # Mise en forme propre de la superficie
    try:
        superficie = f"{int(float(superficie)):,} m²".replace(",", " ")
    except:
        superficie = "N/A"

    # 🔍 Recherche via le nom de commune
    commune_centre = str(selected_data.get("commune", "")).strip().lower()
    df_canopee["nom_commune_clean"] = df_canopee["nom_commune"].str.strip().str.lower()

    canopee_row = df_canopee[df_canopee["nom_commune_clean"] == commune_centre]

    if not canopee_row.empty:
        canopee = canopee_row.iloc[0]
        lot = canopee.get("lot", "N/A")
        fermeture_com = canopee.get("fermeture_commerciale", "N/A")
        fermeture_tech = canopee.get("fermeture_technique", "N/A")
        code_oi = canopee.get("code_oi", "N/A")
        nom_oi = canopee.get("nom_oi", "N/A")
    else:
        lot = fermeture_com = fermeture_tech = code_oi = nom_oi = "N/A"

    # Construction du texte HTML pour l'infobulle
    popup_html = f"""
    <b>{selected_data['nom']}</b><br>
    Type : {type_cc}<br>
    Adresse : {adresse_complete} - {code_postal} {ville}<br>
    Propriétaire : {proprietaire}<br>
    Boutiques : {nb_boutiques}<br>
    Ancienneté : {int(anciennete)} ans<br>
    Superficie : {superficie}
    <br><b>Données Canopée</b><br>
    Lot : {lot}<br>
    Fermeture commerciale : {fermeture_com}<br>
    Fermeture technique : {fermeture_tech}<br>
    Code OI : {code_oi}<br>
    Nom OI : {nom_oi}
    """

    # Ajouter le marker avec infobulle
    folium.Marker(
        location=[selected_data['latitude'], selected_data['longitude']],
        tooltip=popup_html,
        icon=folium.Icon(color='red', icon='shopping-cart', prefix='fa')
    ).add_to(m)
    
    
    # --- Affichage des boutiques vertes du centre ---
    boutiques_vertes_raw = selected_data.get("boutiques_vertes", "")
    if pd.notna(boutiques_vertes_raw) and isinstance(boutiques_vertes_raw, str) and boutiques_vertes_raw.strip():
        boutiques = boutiques_vertes_raw.split(";")
        for boutique in boutiques:
            try:
                # Extraire nom et coordonnées
                name_part, coords_part = boutique.strip().rsplit("(", 1)
                lat_str, lon_str = coords_part.strip(")").split(",")
                lat_b, lon_b = float(lat_str), float(lon_str)

                folium.Marker(
                    location=[lat_b, lon_b],
                    tooltip=name_part.strip(),
                    icon=folium.Icon(color="pink", icon="shopping-cart", prefix='fa')
                ).add_to(m)
            except Exception as e:
                print(f"❌ Erreur parsing boutique verte : {boutique} -> {e}")

    try:
        polygon_coords = convert_to_polygon(selected_data["polygon"])
        polygon_coords = [(lat, lon) for lon, lat in polygon_coords]
        folium.Polygon(locations=polygon_coords, color='blue', fill=True, fill_opacity=0.5).add_to(m)

        filtered_imb = selected_data["imbs"]
        if filtered_imb:
           
            for imb in filtered_imb:
                site_num, xx, yy = imb  # Extrait de la liste dans le CSV principal

                # Rechercher dans df_imb_clean les infos enrichies pour ce SITE - Num
                matched_imb = df_imb[df_imb["SITE - Num"] == site_num]

                if not matched_imb.empty:
                    row = matched_imb.iloc[0]
                    voie = row.get("SITE - voi", "N/A")
                    oi = row.get("OI", "Orange")  # Valeur par défaut si manquant
                    nb_el = row.get("Nb_EL", "N/A")
                else:
                    voie = "N/A"
                    oi = "N/A"
                    nb_el = "N/A"

                # Construction du tooltip enrichi
                tooltip_imb = f"""
                <b>{site_num}</b><br>
                Voie : {voie}<br>
                OI : {oi}<br>
                Nb_EL : {nb_el}
                """

                # Affichage du marqueur sur la carte
                folium.Marker(
                    location=[yy, xx],
                    tooltip=tooltip_imb,
                    icon=folium.Icon(color="blue", icon="info-sign",prefix='fa')
                ).add_to(m)

    except Exception as e:
        st.error(f"Erreur lors de l'ajout du polygone ou IMBS : {e}")

    # Affichage unique de la carte
    clicked_points = st_folium(m, width=1300, height=650)

    # **Premier menu avec options principales**
    option = st.sidebar.selectbox("Choisissez une option", ["Sélectionnez une option", "Calcul Distance"])

    if option == "Calcul Distance":
        st.sidebar.header("Calcul Distance")

        # Initialiser la session pour stocker les points sélectionnés
        if 'selected_points' not in st.session_state:
            st.session_state.selected_points = []

        if st.sidebar.button("Réinitialiser la sélection"):
            st.session_state.selected_points = []

        # Récupération des clics de l'utilisateur
        if clicked_points and clicked_points.get("last_clicked"):
            lat, lon = clicked_points["last_clicked"]["lat"], clicked_points["last_clicked"]["lng"]

            if len(st.session_state.selected_points) < 2:
                st.session_state.selected_points.append((lat, lon))

        # Affichage des points sélectionnés
        if len(st.session_state.selected_points) == 1:
            st.sidebar.write(f"Premier point sélectionné : {st.session_state.selected_points[0]}")
        elif len(st.session_state.selected_points) == 2:
            st.sidebar.write(f"Premier point : {st.session_state.selected_points[0]}")
            st.sidebar.write(f"Deuxième point : {st.session_state.selected_points[1]}")

            # Calcul de la distance
            distance = geodesic(st.session_state.selected_points[0], st.session_state.selected_points[1]).meters
            st.sidebar.write(f"Distance : {distance:.2f} mètres.")

            # Réinitialiser après affichage
            st.session_state.selected_points = []


#filtrer par enseigne
elif selected_enseigne:
    df_matching = df[df['enseignes'].fillna('').str.contains(selected_enseigne, case=False, na=False)]

    if df_matching.empty:
        st.warning(f"Aucun centre trouvé pour l'enseigne : {selected_enseigne}")
    else:
        # Centrer la carte sur le premier résultat
        first = df_matching.iloc[0]
        m = folium.Map(location=[first['latitude'], first['longitude']], zoom_start=6)

        for _, row in df_matching.iterrows():
            adresse_parts = [row.get(f"adresse{i}") for i in range(1, 4) if not pd.isna(row.get(f"adresse{i}"))]
            adresse_complete = ", ".join(adresse_parts)
            ville = row.get("nom_ville", "")
            code_postal = row.get("code_postal", "")
            nb_boutiques = row.get("nb_boutiques", "N/A")
            type_cc = row.get("typologie_cc_long", "")
            proprietaire = row.get("gestionnaires", "N/A")
            superficie = row.get("surface_gla", "N/A")
            anciennete = row.get("nb_annees_ouverture", "N/A")

            try:
                superficie = f"{int(float(superficie)):,} m²".replace(",", " ")
            except:
                superficie = "N/A"

            tooltip_html = f"""
            <b>{row['nom']}</b><br>
            Type : {type_cc}<br>
            Adresse : {adresse_complete} - {code_postal} {ville}<br>
            Propriétaire : {proprietaire}<br>
            Boutiques : {nb_boutiques}<br>
            Ancienneté : {anciennete} ans<br>
            Superficie : {superficie}
            """

            folium.Marker(
                location=[row['latitude'], row['longitude']],
                tooltip=tooltip_html,
                icon=folium.Icon(color='red', icon='shopping-cart',prefix='fa')
            ).add_to(m)

        st_folium(m, width=1300, height=650)
        
        
#filtre par fonciere
elif selected_gestionnaire:
    df_matching = df[df['gestionnaires'] == selected_gestionnaire]

    if df_matching.empty:
        st.warning(f"Aucun centre trouvé pour la foncière : {selected_gestionnaire}")
    else:
        first = df_matching.iloc[0]
        m = folium.Map(location=[first['latitude'], first['longitude']], zoom_start=6)

        for _, row in df_matching.iterrows():
            adresse_parts = [row.get(f"adresse{i}") for i in range(1, 4) if not pd.isna(row.get(f"adresse{i}"))]
            adresse_complete = ", ".join(adresse_parts)
            ville = row.get("nom_ville", "")
            code_postal = row.get("code_postal", "")
            nb_boutiques = row.get("nb_boutiques", "N/A")
            type_cc = row.get("typologie_cc_long", "")
            superficie = row.get("surface_gla", "N/A")
            anciennete = row.get("nb_annees_ouverture", "N/A")

            try:
                superficie = f"{int(float(superficie)):,} m²".replace(",", " ")
            except:
                superficie = "N/A"

            tooltip_html = f"""
            <b>{row['nom']}</b><br>
            Type : {type_cc}<br>
            Adresse : {adresse_complete} - {code_postal} {ville}<br>
            Propriétaire : {selected_gestionnaire}<br>
            Boutiques : {nb_boutiques}<br>
            Ancienneté : {anciennete} ans<br>
            Superficie : {superficie}
            """

            folium.Marker(
                location=[row['latitude'], row['longitude']],
                tooltip=tooltip_html,
                icon=folium.Icon(color='red', icon='shopping-cart', prefix='fa')
            ).add_to(m)

        st_folium(m, width=1300, height=650)
        
#filtre par region
elif selected_region:
    df_matching = df[df['region'] == selected_region]

    if df_matching.empty:
        st.warning(f"Aucun centre trouvé pour la région : {selected_region}")
    else:
        first = df_matching.iloc[0]
        m = folium.Map(location=[first['latitude'], first['longitude']], zoom_start=6)

        for _, row in df_matching.iterrows():
            adresse_parts = [row.get(f"adresse{i}") for i in range(1, 4) if not pd.isna(row.get(f"adresse{i}"))]
            adresse_complete = ", ".join(adresse_parts)
            ville = row.get("nom_ville", "")
            code_postal = row.get("code_postal", "")
            nb_boutiques = row.get("nb_boutiques", "N/A")
            type_cc = row.get("typologie_cc_long", "")
            superficie = row.get("surface_gla", "N/A")
            anciennete = row.get("nb_annees_ouverture", "N/A")
            gestionnaire = row.get("gestionnaires", "N/A")

            try:
                superficie = f"{int(float(superficie)):,} m²".replace(",", " ")
            except:
                superficie = "N/A"

            tooltip_html = f"""
            <b>{row['nom']}</b><br>
            Type : {type_cc}<br>
            Adresse : {adresse_complete} - {code_postal} {ville}<br>
            Propriétaire : {gestionnaire}<br>
            Boutiques : {nb_boutiques}<br>
            Ancienneté : {anciennete} ans<br>
            Superficie : {superficie}
            """

            folium.Marker(
                location=[row['latitude'], row['longitude']],
                tooltip=tooltip_html,
                icon=folium.Icon(color='red', icon='shopping-cart', prefix='fa')
            ).add_to(m)

        st_folium(m, width=1300, height=650)

else:
    st.write("Veuillez faire une sélection pour afficher la carte.")


