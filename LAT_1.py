import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon
import folium
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

@st.cache_data
def create_shapefile_zip(gdf):
    with tempfile.TemporaryDirectory() as temp_dir:
        gdf.to_file(os.path.join(temp_dir, "poligon_puo.shp"))
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    zip_file.write(os.path.join(root, file), arcname=file)
        return zip_buffer.getvalue()

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
    # Pastikan config hanya dipanggil sekali
    try:
        st.set_page_config(page_title="PUO Geomatik - WebGIS", layout="wide")
    except:
        pass

    # Sidebar
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/ms/thumb/0/05/Logo_PUO.png/200px-Logo_PUO.png", width=150)
    st.sidebar.header("⚙️ Kawalan Lapisan")
    
    # Task 3 & 4: Toggles
    on_off_satelit = st.sidebar.radio("🗺️ Jenis Peta", ["Satelit (Esri)", "Peta Standard (OSM)"])
    on_off_bearing = st.sidebar.checkbox("📏 Papar Bearing & Jarak", value=True)
    on_off_label = st.sidebar.checkbox("🏷️ Papar Label Stesen", value=True)
    
    # Kod EPSG amat penting untuk penukaran ke Lat/Long (WGS84) supaya muncul di peta dunia
    epsg_input = st.sidebar.text_input("🌍 Kod EPSG Asal (Contoh: 3380 untuk Perak)", value="3380")
    
    if st.sidebar.button("Keluar (Logout)"):
        st.session_state.logged_in = False
        st.rerun()

    st.markdown("## 🛰️ PUO WebGIS Plotter (Interactive)")
    st.divider()

    uploaded_file = st.file_uploader("📂 Muat naik fail CSV (Format: STN, E, N)", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        
        # Penukaran Koordinat ke WGS84 untuk Folium (Peta Web guna Lat/Long)
        try:
            gdf_raw = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.E, df.N), crs=f"EPSG:{epsg_input}")
            gdf_wgs84 = gdf_raw.to_crs(epsg="4326") # Tukar ke Lat/Long
            df['lat'] = gdf_wgs84.geometry.y
            df['lon'] = gdf_wgs84.geometry.x
        except Exception as e:
            st.error(f"Ralat Koordinat: Sila pastikan Kod EPSG betul. {e}")

        tab1, tab2 = st.tabs(["📊 Peta Interaktif", "📥 Eksport Data"])

        with tab1:
            # Pengiraan Luas
            luas = kira_luas(df['E'].values, df['N'].values)
            st.metric("Luas Poligon", f"{luas:.3f} m²")

            # Mencipta Peta Folium
            center_lat = df['lat'].mean()
            center_lon = df['lon'].mean()
            
            tile_provider = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attr = "Esri World Imagery"
            
            if on_off_satelit == "Peta Standard (OSM)":
                m = folium.Map(location=[center_lat, center_lon], zoom_start=18)
            else:
                m = folium.Map(location=[center_lat, center_lon], zoom_start=18, tiles=tile_provider, attr=attr)

            # Melukis Poligon
            coords = list(zip(df.lat, df.lon))
            folium.Polygon(locations=coords, color="yellow", weight=3, fill=True, fill_opacity=0.2).add_to(m)

            # Task 4: Label & Marker
            for i, row in df.iterrows():
                if on_off_label:
                    folium.Marker(
                        location=[row.lat, row.lon],
                        icon=folium.DivIcon(html=f"""<div style="font-family: sans-serif; color: white; background: rgba(0,0,0,0.5); padding: 2px; border-radius: 3px;"><b>{int(row.STN)}</b></div>"""),
                    ).add_to(m)
                
                # Tambah Tooltip Info
                folium.CircleMarker(location=[row.lat, row.lon], radius=3, color="red").add_to(m)

            # Papar Peta dalam Streamlit
            st_folium(m, width=1100, height=600)

        with tab2:
            st.subheader("📥 Muat Turun")
            geom = Polygon(list(zip(df.E, df.N)))
            gdf_export = gpd.GeoDataFrame(index=[0], geometry=[geom], crs=f"EPSG:{epsg_input}")
            
            c1, c2 = st.columns(2)
            c1.download_button("🗺️ Simpan GeoJSON", data=gdf_export.to_json(), file_name="puo_map.geojson")
            
            shp_zip = create_shapefile_zip(gdf_export)
            c2.download_button("📁 Simpan Shapefile (ZIP)", data=shp_zip, file_name="puo_shp.zip")
    else:
        st.info("Sila muat naik fail CSV.")
