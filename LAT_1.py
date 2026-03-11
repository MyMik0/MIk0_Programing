import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon
import folium
from folium import plugins
from streamlit_folium import st_folium
import io
import zipfile
import tempfile
import os

# --- 1. FUNGSI MATEMATIK & GEOMATIK ---

def to_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = round((((deg - d) * 60) - m) * 60, 0)
    if s == 60: m += 1; s = 0
    if m == 60: d += 1; m = 0
    return f"{d}°{m:02d}'{s:02.0f}\""

def kira_bearing_jarak(p1, p2):
    de = p2[0] - p1[0]
    dn = p2[1] - p1[1]
    jarak = np.sqrt(de**2 + dn**2)
    angle = np.degrees(np.arctan2(de, dn))
    bearing = angle if angle >= 0 else angle + 360
    return to_dms(bearing), jarak, bearing

def kira_luas(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

# --- FUNGSI EKSPORT KE GIS ---
def create_shapefile_zip(gdf):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_name = "poligon_gis_puo"
            path = os.path.join(temp_dir, f"{base_name}.shp")
            # Menggunakan engine pyogrio untuk kelancaran eksport
            gdf.to_file(path, engine="pyogrio") 
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        zip_file.write(os.path.join(root, file), arcname=file)
            return zip_buffer.getvalue()
    except Exception as e:
        st.error(f"Ralat Eksport: {e}")
        return None

# --- 2. SISTEM LOG MASUK ---

def semak_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.set_page_config(page_title="Log Masuk | PUO Geomatik", page_icon="🔐")
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st.image("https://upload.wikimedia.org/wikipedia/ms/thumb/0/05/Logo_PUO.png/200px-Logo_PUO.png", width=100)
            st.subheader("🔐 Log Masuk Sistem Poligon")
            user = st.text_input("ID Pengguna")
            pw = st.text_input("Kata Laluan", type="password")
            if st.button("Masuk", use_container_width=True):
                if user == "admin123" and pw == "123456":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("ID atau Kata Laluan Salah!")
        return False
    return True

# --- 3. APLIKASI UTAMA ---

if semak_login():
    try:
        st.set_page_config(page_title="PUO Geomatik - WebGIS", layout="wide")
    except:
        pass

    # Sidebar
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/ms/thumb/0/05/Logo_PUO.png/200px-Logo_PUO.png", width=150)
    st.sidebar.header("⚙️ Kawalan Lapisan")
    
    on_off_satelit = st.sidebar.radio("🗺️ Jenis Peta", ["Satelit (Google Hybrid)", "Peta Standard (OSM)"])
    on_off_bearing = st.sidebar.checkbox("📏 Papar Bearing & Jarak", value=True)
    on_off_label = st.sidebar.checkbox("🏷️ Papar Label Stesen", value=True)
    
    epsg_input = st.sidebar.text_input("🌍 Kod EPSG Asal (Contoh: 4390 - Johor)", value="4390")
    
    if st.sidebar.button("Keluar (Logout)"):
        st.session_state.logged_in = False
        st.rerun()

    st.markdown("## 🛰️ PUO WebGIS Plotter (Interactive)")
    st.divider()

    uploaded_file = st.file_uploader("📂 Muat naik fail CSV (Format: STN, E, N)", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        
        try:
            # Penukaran Koordinat ke WGS84
            gdf_raw = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.E, df.N), crs=f"EPSG:{epsg_input}")
            gdf_wgs84 = gdf_raw.to_crs(epsg="4326")
            df['lat'] = gdf_wgs84.geometry.y
            df['lon'] = gdf_wgs84.geometry.x

            tab1, tab2 = st.tabs(["📊 Peta Interaktif", "📥 Eksport Data GIS"])

            with tab1:
                luas = kira_luas(df['E'].values, df['N'].values)
                st.metric("Luas Poligon", f"{luas:.3f} m²")

                # Konfigurasi Peta
                center_lat, center_lon = df['lat'].mean(), df['lon'].mean()
                google_hybrid = "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"
                
                if on_off_satelit == "Satelit (Google Hybrid)":
                    m = folium.Map(location=[center_lat, center_lon], zoom_start=19, tiles=google_hybrid, attr="Google")
                else:
                    m = folium.Map(location=[center_lat, center_lon], zoom_start=19)

                # Tambah Skala & Skrin Penuh
                folium.plugins.Fullscreen().add_to(m)
                folium.MeasureControl(position='topleft', primary_length_unit='meters').add_to(m)

                # Lukis Poligon
                coords = list(zip(df.lat, df.lon))
                folium.Polygon(locations=coords, color="yellow", weight=3, fill=True, fill_opacity=0.2).add_to(m)

                # Auto-Zoom ke Poligon
                m.fit_bounds(coords)

                # Papar Bearing & Jarak
                if on_off_bearing:
                    for i in range(len(df)):
                        p1 = (df.iloc[i]['E'], df.iloc[i]['N'])
                        p2 = (df.iloc[(i + 1) % len(df)]['E'], df.iloc[(i + 1) % len(df)]['N'])
                        b_text, d_val, _ = kira_bearing_jarak(p1, p2)
                        
                        mid_lat = (df.iloc[i]['lat'] + df.iloc[(i + 1) % len(df)]['lat']) / 2
                        mid_lon = (df.iloc[i]['lon'] + df.iloc[(i + 1) % len(df)]['lon']) / 2
                        
                        folium.Marker(
                            location=[mid_lat, mid_lon],
                            icon=folium.DivIcon(html=f"""<div style="font-size: 9pt; color: #00FFFF; font-weight: bold; text-shadow: 1px 1px #000; width: 150px;">{b_text}<br>{d_val:.2f}m</div>""")
                        ).add_to(m)

                # Papar Label Stesen
                for i, row in df.iterrows():
                    if on_off_label:
                        folium.Marker(
                            location=[row.lat, row.lon],
                            icon=folium.DivIcon(html=f"""<div style="color: white; background: rgba(0,0,0,0.6); padding: 2px 5px; border-radius: 4px; font-size: 10px; border: 1px solid white;"><b>{int(row.STN)}</b></div>"""),
                        ).add_to(m)
                    folium.CircleMarker(location=[row.lat, row.lon], radius=4, color="red", fill=True).add_to(m)

                st_folium(m, width=1100, height=600, key="webgis_final")

            with tab2:
                st.subheader("📥 Muat Turun untuk GIS")
                geom = Polygon(list(zip(df.E, df.N)))
                gdf_export = gpd.GeoDataFrame(index=[0], geometry=[geom], crs=f"EPSG:{epsg_input}")
                
                c1, c2 = st.columns(2)
                with c1:
                    st.info("GeoJSON sesuai untuk QGIS & Google Earth.")
                    st.download_button("🗺️ Muat Turun GeoJSON", data=gdf_export.to_json(), file_name="poligon_puo.geojson")
                
                with c2:
                    st.info("Shapefile sesuai untuk ArcGIS/Professional GIS.")
                    shp_zip = create_shapefile_zip(gdf_export)
                    if shp_zip:
                        st.download_button("📁 Muat Turun Shapefile (ZIP)", data=shp_zip, file_name="poligon_puo_shp.zip")

        except Exception as e:
            st.error(f"Sila pastikan format CSV betul (STN, E, N) dan Kod EPSG tepat. Ralat: {e}")
    else:
        st.info("Sila muat naik fail CSV untuk memulakan pemetaan.")
