import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd  # Ini yang betul, bukan import gpd
from shapely.geometry import Polygon
import folium
from folium.plugins import MeasureControl, Fullscreen
from streamlit_folium import st_folium
import io
import zipfile
import tempfile
import os
import time

# ==========================================
# --- 0. KONFIGURASI HALAMAN ---
# ==========================================
st.set_page_config(page_title="PUO Geomatik - WebGIS Pro", layout="wide", page_icon="🛰️")

# ==========================================
# --- 1. FUNGSI INTRO VIDEO (HEALING) ---
# ==========================================
def video_healing_intro():
    if st.session_state.get("logged_in") and not st.session_state.get("intro_done"):
        placeholder = st.empty()
        with placeholder.container():
            st.markdown("""
                <style>
                .intro-video-container {
                    position: fixed;
                    top: 0; left: 0; width: 100vw; height: 100vh;
                    overflow: hidden; z-index: 99999; background: black;
                }
                video { width: 100%; height: 100%; object-fit: cover; }
                .intro-text {
                    position: absolute; top: 50%; left: 50%;
                    transform: translate(-50%, -50%); color: white;
                    text-align: center; font-family: 'Arial', sans-serif; z-index: 100000;
                }
                </style>
                <div class="intro-video-container">
                    <video autoplay muted playsinline>
                        <source src="PROM.mp4" type="video/mp4">
                    </video>
                    <div class="intro-text">
                        <h1 style="font-size: 4rem; letter-spacing: 10px; margin-bottom: 0;">PUO GEOMATIK</h1>
                        <p style="font-size: 1.5rem; font-style: italic; opacity: 0.8;">Sistem Sedang Dimuatkan...</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            time.sleep(7)  # Tayangan intro selama 7 saat
            st.session_state.intro_done = True
            placeholder.empty()
            st.rerun()

# ==========================================
# --- 2. FUNGSI TEKNIKAL GEOMATIK ---
# ==========================================
def to_dms(deg):
    d = int(deg); m = int((deg - d) * 60); s = round((((deg - d) * 60) - m) * 60, 0)
    if s == 60: m += 1; s = 0
    if m == 60: d += 1; m = 0
    return f"{d}°{m:02d}'{s:02.0f}\""

def kira_bearing_jarak(p1, p2):
    de = p2[0] - p1[0]; dn = p2[1] - p1[1]
    jarak = np.sqrt(de**2 + dn**2)
    angle = np.degrees(np.arctan2(de, dn))
    bearing = angle if angle >= 0 else angle + 360
    return to_dms(bearing), jarak, bearing

def kira_luas(x, y):
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))

def create_shapefile_zip(gdf):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "poligon_puo.shp")
            gdf.to_file(path, engine="pyogrio") 
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                for root, _, files in os.walk(temp_dir):
                    for file in files: zip_file.write(os.path.join(root, file), arcname=file)
            return zip_buffer.getvalue()
    except Exception as e:
        st.error(f"Ralat Eksport: {e}"); return None

# ==========================================
# --- 3. SISTEM LOG MASUK ---
# ==========================================
def semak_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st.markdown("""
                <div style="background:#f9f9f9; padding:30px; border-radius:15px; text-align:center; box-shadow:0 4px 10px rgba(0,0,0,0.1);">
                    <img src="https://upload.wikimedia.org/wikipedia/ms/thumb/0/05/Logo_PUO.png/200px-Logo_PUO.png" width="100">
                    <h3>🔐 Log Masuk PUO Geomatik</h3>
                </div>
            """, unsafe_allow_html=True)
            user = st.text_input("ID Pengguna")
            pw = st.text_input("Kata Laluan", type="password")
            if st.button("Masuk Sekarang", use_container_width=True):
                if user == "admin123" and pw == "123456":
                    st.session_state.logged_in = True
                    st.session_state.intro_done = False 
                    st.rerun()
                else:
                    st.error("ID atau Kata Laluan Salah!")
        return False
    return True

# ==========================================
# --- 4. ALIRAN EKSEKUSI UTAMA ---
# ==========================================
if semak_login():
    # Jalankan Intro Video Fullscreen
    video_healing_intro()

    import base64

# Fungsi untuk tukar video kepada format yang boleh dibaca browser
def get_video_base64(video_path):
    with open(video_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Tukar fail PROM.mp4 anda
try:
    video_base64 = get_video_base64("PROM.mp4")
    video_src = f"data:video/mp4;base64,{video_base64}"
except:
    video_src = "" # Jika fail tak jumpa

# --- KEMASKINI BAHAGIAN HTML HEADER ---
st.markdown(f"""
    <style>
    .header-box {{
        position: relative;
        width: 100%;
        height: 280px;
        overflow: hidden;
        border-radius: 25px;
        margin-bottom: 30px;
        display: flex;
        justify-content: center;
        align-items: center;
        border-bottom: 5px solid #ffcc00;
        box-shadow: 0 15px 35px rgba(0,0,0,0.4);
    }}
    .header-video {{
        position: absolute;
        top: 50%; left: 50%;
        min-width: 100%; min-height: 100%;
        z-index: 0; transform: translate(-50%, -50%);
        filter: brightness(40%) contrast(110%);
        object-fit: cover;
    }}
    .header-content {{
        position: relative; z-index: 1;
        color: white; text-align: center;
    }}
    .header-signature {{
        position: absolute;
        bottom: 15px; right: 25px;
        z-index: 2; color: white;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem; letter-spacing: 2px;
        opacity: 0.7; text-transform: uppercase;
    }}
    </style>

    <div class="header-box">
        <video autoplay muted loop playsinline class="header-video">
            <source src="{video_src}" type="video/mp4">
        </video>
        <div class="header-content">
            <h1 style='font-size: 3.5rem; letter-spacing: 3px; margin: 0;'>🛰️ PUO WEB-GIS PRO-PLOTTER</h1>
            <p style='font-size: 1.3rem; opacity: 0.9; font-style: italic;'>Precision Mapping & Visual Healing Experience</p>
        </div>
        <div class="header-signature">
            Developed by: <b>AHMAD ILHAM</b>
        </div>
    </div>
""", unsafe_allow_html=True)

    # --- SIDEBAR ---
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/ms/thumb/0/05/Logo_PUO.png/200px-Logo_PUO.png", width=150)
    st.sidebar.header("⚙️ Konfigurasi")
    on_off_satelit = st.sidebar.radio("🗺️ Jenis Peta", ["Satelit (Google)", "Standard (OSM)"])
    on_off_bearing = st.sidebar.checkbox("📏 Papar Bearing/Jarak", value=True)
    on_off_label = st.sidebar.checkbox("🏷️ Papar Label Stesen", value=True)
    epsg_input = st.sidebar.text_input("🌍 Kod EPSG", value="4390")
    
    if st.sidebar.button("Keluar Sistem"):
        st.session_state.logged_in = False
        st.session_state.intro_done = False
        st.rerun()

    # --- INPUT FAIL CSV ---
    uploaded_file = st.file_uploader("📂 Muat naik fail CSV Koordinat (STN, E, N)", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        try:
            # Transformasi Koordinat
            gdf_raw = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.E, df.N), crs=f"EPSG:{epsg_input}")
            gdf_wgs84 = gdf_raw.to_crs(epsg="4326")
            df['lat'] = gdf_wgs84.geometry.y
            df['lon'] = gdf_wgs84.geometry.x

            tab1, tab2 = st.tabs(["📊 Paparan Peta Interaktif", "📥 Eksport Data"])

            with tab1:
                st.metric("Keluasan Poligon (m²)", f"{kira_luas(df['E'].values, df['N'].values):.3f}")
                
                center = [df['lat'].mean(), df['lon'].mean()]
                if on_off_satelit == "Satelit (Google)":
                    m = folium.Map(location=center, zoom_start=22, max_zoom=22, tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", attr="Google")
                else:
                    m = folium.Map(location=center, zoom_start=20, max_zoom=22)

                Fullscreen().add_to(m)
                MeasureControl(position='topleft').add_to(m)
                
                coords = list(zip(df.lat, df.lon))
                folium.Polygon(locations=coords, color="yellow", weight=3, fill=True, fill_opacity=0.25).add_to(m)
                m.fit_bounds(coords)

                if on_off_bearing:
                    for i in range(len(df)):
                        p1, p2 = (df.iloc[i]['E'], df.iloc[i]['N']), (df.iloc[(i + 1) % len(df)]['E'], df.iloc[(i + 1) % len(df)]['N'])
                        b_text, d_val, b_deg = kira_bearing_jarak(p1, p2)
                        display_angle = b_deg - 90
                        if 90 < b_deg < 270: display_angle += 180

                        folium.Marker(
                            location=[(df.iloc[i]['lat'] + df.iloc[(i + 1) % len(df)]['lat']) / 2, (df.iloc[i]['lon'] + df.iloc[(i + 1) % len(df)]['lon']) / 2],
                            icon=folium.DivIcon(html=f'<div style="transform: rotate({display_angle}deg); color: #00FFFF; font-weight: bold; text-shadow: 2px 2px 4px #000; font-size: 9pt; text-align:center; width:100px; margin-left:-50px;">{b_text}<br>{d_val:.2f}m</div>')
                        ).add_to(m)

                for i, row in df.iterrows():
                    if on_off_label:
                        folium.Marker(location=[row.lat, row.lon], icon=folium.DivIcon(html=f'<div style="color: white; background: rgba(0,0,0,0.7); padding: 2px 5px; border-radius: 5px; font-size: 10px; border: 1px solid #ffcc00;"><b>{int(row.STN)}</b></div>')).add_to(m)
                    folium.CircleMarker(location=[row.lat, row.lon], radius=4, color="red", fill=True).add_to(m)

                st_folium(m, width=1200, height=600, key="main_map")

            with tab2:
                st.subheader("📥 Muat Turun Hasil Pemetaan")
                geom = Polygon(list(zip(df.E, df.N)))
                gdf_export = gpd.GeoDataFrame(index=[0], geometry=[geom], crs=f"EPSG:{epsg_input}")
                st.download_button("🗺️ Muat Turun GeoJSON", data=gdf_export.to_json(), file_name="poligon_puo.geojson")
                shp_zip = create_shapefile_zip(gdf_export)
                if shp_zip: st.download_button("📁 Muat Turun Shapefile (ZIP)", data=shp_zip, file_name="poligon_shp.zip")

        except Exception as e:
            st.error(f"⚠️ Ralat: {e}")
    else:
        st.info("💡 Sila muat naik fail CSV koordinat untuk memulakan pemetaan.")

