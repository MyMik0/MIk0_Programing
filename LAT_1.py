import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, LineString
import folium
from folium.plugins import MeasureControl, Fullscreen
from streamlit_folium import st_folium
import io
import zipfile
import tempfile
import os
import time
import base64

# ==========================================
# --- 0. KONFIGURASI HALAMAN ---
# ==========================================
st.set_page_config(page_title="PUO Geomatik - WebGIS Pro", layout="wide", page_icon="🛰️")

def get_video_base64(video_path):
    try:
        if os.path.exists(video_path):
            with open(video_path, "rb") as f:
                data = f.read()
            return base64.b64encode(data).decode()
        return None
    except:
        return None

# ==========================================
# --- 1. FUNGSI INTRO VIDEO (HEALING) ---
# ==========================================
def video_healing_intro(v_src):
    if st.session_state.get("logged_in") and not st.session_state.get("intro_done"):
        placeholder = st.empty()
        with placeholder.container():
            st.markdown(f"""
                <style>
                .intro-video-container {{
                    position: fixed;
                    top: 0; left: 0; width: 100vw; height: 100vh;
                    overflow: hidden; z-index: 99999; background: black;
                }}
                video {{ width: 100%; height: 100%; object-fit: cover; }}
                .intro-text {{
                    position: absolute; top: 50%; left: 50%;
                    transform: translate(-50%, -50%); color: white;
                    text-align: center; font-family: 'Arial', sans-serif; z-index: 100000;
                }}
                </style>
                <div class="intro-video-container">
                    <video autoplay muted playsinline>
                        <source src="data:video/mp4;base64,{v_src}" type="video/mp4">
                    </video>
                    <div class="intro-text">
                        <h1 style="font-size: 4rem; letter-spacing: 10px; margin-bottom: 0;">PUO GEOMATIK</h1>
                        <p style="font-size: 1.5rem; font-style: italic; opacity: 0.8;">Sistem Sedang Dimuatkan...</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            time.sleep(7)
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
            path = os.path.join(temp_dir, "data_geomatik.shp")
            gdf.to_file(path, engine="pyogrio") 
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                for root, _, files in os.walk(temp_dir):
                    for file in files: zip_file.write(os.path.join(root, file), arcname=file)
            return zip_buffer.getvalue()
    except Exception as e:
        st.error(f"Ralat Eksport Shapefile: {e}"); return None

# ==========================================
# --- 3. SISTEM LOG MASUK (3 ID, 1 PW) ---
# ==========================================
def semak_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.markdown("""
            <style>
            .login-container {
                background: rgba(255, 255, 255, 0.05);
                backdrop-filter: blur(15px);
                padding: 40px; border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
                text-align: center; margin-top: 50px;
            }
            .stButton>button {
                background: linear-gradient(45deg, #800000, #b30000);
                color: white; border-radius: 10px; border: none;
                padding: 10px 20px; font-weight: bold; transition: 0.3s;
            }
            </style>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1.2, 1])
        with col2:
            st.markdown("""
                <div class="login-container">
                    <img src="https://upload.wikimedia.org/wikipedia/ms/thumb/0/05/Logo_PUO.png/200px-Logo_PUO.png" width="120">
                    <h2 style='color:#800000;'>GEO-TECH PRO</h2>
                </div>
            """, unsafe_allow_html=True)
            user = st.text_input("👤 ID Pengguna", placeholder="admin123 / admin124 / admin125")
            pw = st.text_input("🔑 Kata Laluan", type="password", placeholder="******")
            
            senarai_id = ["admin123", "admin124", "admin125"]
            if st.button("PENGESAHAN MASUK", use_container_width=True):
                if user in senarai_id and pw == "123456":
                    st.session_state.logged_in = True
                    st.session_state.intro_done = False 
                    st.session_state.current_user = user
                    st.rerun()
                else:
                    st.error("ID atau Kata Laluan Salah!")
        return False
    return True

# ==========================================
# --- 4. ALIRAN UTAMA ---
# ==========================================
if semak_login():
    video_data = get_video_base64("PROM.mp4")
    if video_data: video_healing_intro(video_data)

    st.markdown(f"""
        <div style="position: relative; width: 100%; height: 280px; overflow: hidden; border-radius: 25px; margin-bottom: 30px; display: flex; justify-content: center; align-items: center; border-bottom: 5px solid #ffcc00; box-shadow: 0 15px 35px rgba(0,0,0,0.4); background: black;">
            <video autoplay muted loop playsinline style="position: absolute; min-width: 100%; min-height: 100%; filter: brightness(40%); object-fit: cover;">
                <source src="data:video/mp4;base64,{video_data if video_data else ''}" type="video/mp4">
            </video>
            <div style="position: relative; color: white; text-align: center;">
                <h1 style='font-size: 3.5rem;'>🛰️ PUO WEB-GIS PRO-PLOTTER</h1>
                <p>Developed by: <b>AHMAD ILHAM</b></p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # SIDEBAR
    user_aktif = st.session_state.get("current_user", "Pengguna")
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/ms/thumb/0/05/Logo_PUO.png/200px-Logo_PUO.png", width=120)
    st.sidebar.write(f"👤 Pengguna: **{user_aktif}**")
    on_off_satelit = st.sidebar.radio("🗺️ Peta", ["Satelit (Google)", "Standard (OSM)"])
    on_off_bearing = st.sidebar.checkbox("📏 Bearing/Jarak", value=True)
    on_off_label = st.sidebar.checkbox("🏷️ Label Stesen", value=True)
    epsg_input = st.sidebar.text_input("🌍 EPSG", value="4390")
    if st.sidebar.button("LOG KELUAR"):
        st.session_state.logged_in = False
        st.rerun()

    uploaded_file = st.file_uploader("📂 Muat naik CSV (STN, E, N)", type=["csv"])

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        try:
            gdf_raw = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.E, df.N), crs=f"EPSG:{epsg_input}")
            gdf_wgs84 = gdf_raw.to_crs(epsg="4326")
            df['lat'], df['lon'] = gdf_wgs84.geometry.y, gdf_wgs84.geometry.x

            tab1, tab2 = st.tabs(["📊 Peta Interaktif", "📥 Eksport GIS Lengkap"])

            with tab1:
                st.metric("Keluasan (m²)", f"{kira_luas(df['E'].values, df['N'].values):.3f}")
                m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=20, max_zoom=22)
                if on_off_satelit == "Satelit (Google)":
                    folium.TileLayer("https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", attr="Google", name="Google Satellite").add_to(m)
                
                coords = list(zip(df.lat, df.lon))
                folium.Polygon(locations=coords, color="yellow", fill=True, fill_opacity=0.3).add_to(m)
                
                if on_off_bearing:
                    for i in range(len(df)):
                        p1, p2 = (df.iloc[i]['E'], df.iloc[i]['N']), (df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N'])
                        b_text, d_val, b_deg = kira_bearing_jarak(p1, p2)
                        folium.Marker(location=[(df.iloc[i]['lat']+df.iloc[(i+1)%len(df)]['lat'])/2, (df.iloc[i]['lon']+df.iloc[(i+1)%len(df)]['lon'])/2],
                                      icon=folium.DivIcon(html=f'<div style="color:#00FFFF; font-size:9pt; font-weight:bold; text-align:center; width:100px; margin-left:-50px;">{b_text}<br>{d_val:.2f}m</div>')).add_to(m)
                
                for i, row in df.iterrows():
                    if on_off_label: folium.Marker([row.lat, row.lon], icon=folium.DivIcon(html=f'<div style="color:white; background:rgba(128,0,0,0.8); padding:2px; border-radius:5px; font-size:10px;"><b>{int(row.STN)}</b></div>')).add_to(m)
                    folium.CircleMarker([row.lat, row.lon], radius=4, color="red").add_to(m)
                
                Fullscreen().add_to(m); MeasureControl().add_to(m)
                st_folium(m, width=1200, height=600)

            with tab2:
                st.subheader("📥 Muat Turun Data Geomatik Lengkap")
                
                # Bina Poligon
                gdf_poly = gpd.GeoDataFrame({'unsur': ['Kawasan'], 'geometry': [Polygon(list(zip(df.E, df.N)))]}, crs=f"EPSG:{epsg_input}")
                
                # Bina Point Stesen
                gdf_pts = gpd.GeoDataFrame(df[['STN', 'E', 'N']], geometry=gpd.points_from_xy(df.E, df.N), crs=f"EPSG:{epsg_input}")
                
                # Bina Line Traves (Lengkap Bearing/Jarak)
                lines = []
                for i in range(len(df)):
                    p1, p2 = (df.iloc[i]['E'], df.iloc[i]['N']), (df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N'])
                    b_text, d_val, _ = kira_bearing_jarak(p1, p2)
                    lines.append({'geometry': LineString([p1, p2]), 'bearing': b_text, 'jarak_m': round(d_val,3), 'stn_mula': int(df.iloc[i]['STN']), 'stn_akhir': int(df.iloc[(i+1)%len(df)]['STN'])})
                gdf_lines = gpd.GeoDataFrame(lines, crs=f"EPSG:{epsg_input}")

                # Gabung Semua untuk GeoJSON
                gdf_full = pd.concat([gdf_poly, gdf_pts, gdf_lines], ignore_index=True)
                st.download_button("🗺️ Muat Turun GeoJSON (Semua Unsur)", data=gdf_full.to_json(), file_name="puo_traves_lengkap.geojson")
                
                # Shapefile (ZIP)
                shp_zip = create_shapefile_zip(gdf_full)
                if shp_zip: st.download_button("📁 Muat Turun Shapefile (ZIP)", data=shp_zip, file_name="puo_shp_lengkap.zip")
                st.info("Fail mengandungi lapisan Poligon, Stesen (Points), dan Garisan (Lines) beserta data bearing/jarak.")

        except Exception as e: st.error(f"⚠️ Ralat: {e}")
