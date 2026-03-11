import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon
import contextily as ctx
import io
import zipfile
import tempfile
import os
import requests
from streamlit_lottie import st_lottie  # Perlu tambah dalam requirements.txt

# --- 1. FUNGSI VISUAL BERGERAK (LOTTIE) ---
def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# Animasi Geomatik/Map
lottie_geo = load_lottieurl("https://assets.lottiefiles.com/packages/lf20_5njp7v9p.json") # Animasi globe/map

# --- 2. FUNGSI MATEMATIK & GEOMATIK ---

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

# --- 3. SISTEM LOG MASUK ---

def semak_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.set_page_config(page_title="Log Masuk | PUO Geomatik", page_icon="🔐")
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st_lottie(lottie_geo, height=150, key="login_geo") # Animasi bergerak di login
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

# --- 4. APLIKASI UTAMA ---

if semak_login():
    st.set_page_config(page_title="PUO Geomatik - WebGIS", layout="wide")

    # --- HEADER VISUAL BERGERAK ---
    head_col1, head_col2 = st.columns([1, 4])
    with head_col1:
        st_lottie(lottie_geo, height=120, key="main_geo") # Animasi bergerak di header utama
    with head_col2:
        st.markdown("""
            <h1 style='margin-bottom:0;'>POLITEKNIK UNGKU OMAR</h1>
            <p style='font-size:1.5rem; color: #007BFF;'><b>Jabatan Kejuruteraan Geomatik - WebGIS Plotter</b></p>
            <marquee style='color: gray; font-size: 0.9rem;'>Selamat Datang ke Sistem Plot Poligon Automatik v2.0 - Sila muat naik fail CSV anda untuk memulakan pemetaan...</marquee>
        """, unsafe_allow_html=True)
    
    st.divider()

    # Sidebar
    st.sidebar.header("⚙️ Kawalan Lapisan")
    on_off_satelit = st.sidebar.checkbox("🌍 Imej Satelit (Task 3)", value=False)
    on_off_bearing = st.sidebar.checkbox("📏 Bearing & Jarak", value=True)
    on_off_label = st.sidebar.checkbox("🏷️ Label Stesen", value=True)
    epsg_code = st.sidebar.text_input("Kod EPSG (Satelit)", value="3380")
    
    if st.sidebar.button("Keluar (Logout)"):
        st.session_state.logged_in = False
        st.rerun()

    # Upload Fail
    uploaded_file = st.file_uploader("📂 Muat naik fail CSV (Format: STN, E, N)", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        
        tab1, tab2 = st.tabs(["📊 Data & Peta", "📥 Eksport Fail"])

        with tab1:
            col_data, col_map = st.columns([1, 2.5])
            
            with col_data:
                st.write("### Jadual Koordinat")
                st.dataframe(df.set_index('STN'), height=400)
                btn_luas = st.button("📐 Kira Luas Poligon", use_container_width=True)
                if btn_luas:
                    st.session_state.tampilkan_luas = True

            with col_map:
                if 'E' in df.columns and 'N' in df.columns:
                    fig, ax = plt.subplots(figsize=(10, 10))
                    points = df[['E', 'N']].values
                    n_points = len(points)
                    cx, cy = np.mean(df['E']), np.mean(df['N'])

                    # Lukis Garisan
                    for i in range(n_points):
                        p1, p2 = points[i], points[(i + 1) % n_points]
                        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color='black', marker='o', 
                                linewidth=2, markersize=5, markerfacecolor='white', zorder=4)

                        if on_off_bearing:
                            brg_s, dist, brg_v = kira_bearing_jarak(p1, p2)
                            mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
                            ax.text(mid_x, mid_y, f"{brg_s}\n{dist:.2f}m", color='red', 
                                    fontsize=8, fontweight='bold', ha='center', zorder=5)

                    if on_off_label:
                        for _, row in df.iterrows():
                            ax.text(row['E'], row['N'], f" {int(row['STN'])}", fontsize=10, 
                                    fontweight='bold', bbox=dict(facecolor='yellow', alpha=0.5))

                    if st.session_state.get('tampilkan_luas', False):
                        luas = kira_luas(df['E'].values, df['N'].values)
                        ax.fill(df['E'], df['N'], alpha=0.2, color='green')
                        ax.text(cx, cy, f"LUAS\n{luas:.2f} m²", fontsize=14, color='darkgreen', 
                                ha='center', bbox=dict(facecolor='white', alpha=0.7))

                    if on_off_satelit:
                        try:
                            ctx.add_basemap(ax, crs=f"EPSG:{epsg_code}", source=ctx.providers.Esri.WorldImagery)
                        except:
                            st.warning("Gagal muat satelit. Pastikan koordinat betul.")

                    ax.set_aspect('equal')
                    st.pyplot(fig)

        with tab2:
            st.subheader("📥 Muat Turun Data Geospasial")
            geom = Polygon(points)
            gdf = gpd.GeoDataFrame(index=[0], geometry=[geom], crs=f"EPSG:{epsg_code}")
            
            c1, c2 = st.columns(2)
            c1.download_button("🗺️ Simpan GeoJSON", data=gdf.to_json(), file_name="peta_puo.geojson")
            
            shp_zip = create_shapefile_zip(gdf)
            c2.download_button("📁 Simpan Shapefile (ZIP)", data=shp_zip, file_name="peta_puo_shp.zip")
    else:
        st.info("Sila muat naik fail CSV untuk bermula.")
