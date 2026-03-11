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
# --- 1. FUNGSI INTRO VIDEO ---
# ==========================================
def video_healing_intro(v_src):
    if st.session_state.get("logged_in") and not st.session_state.get("intro_done"):
        placeholder = st.empty()
        with placeholder.container():
            st.markdown(f"""
                <style>
                .intro-video-container {{
                    position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                    overflow: hidden; z-index: 99999; background: black;
                }}
                video {{ width: 100%; height: 100%; object-fit: cover; }}
                </style>
                <div class="intro-video-container">
                    <video autoplay muted playsinline>
                        <source src="data:video/mp4;base64,{v_src}" type="video/mp4">
                    </video>
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
    bearing_deg = angle if angle >= 0 else angle + 360
    
    # Pengiraan pusingan label (CSS Rotation)
    # Kita guna -angle kerana koordinat skrin/peta berpusing ikut jam
    css_rot = -angle 
    # Adjust supaya teks tidak terbalik (upside down)
    if css_rot < -90: css_rot += 180
    if css_rot > 90: css_rot -= 180
    
    return to_dms(bearing_deg), jarak, css_rot

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
        st.error(f"Ralat Eksport: {e}"); return None

# ==========================================
# --- 3. SISTEM LOG MASUK ---
# ==========================================
def semak_login():
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        col1, col2, col3 = st.columns([1, 1.2, 1])
        with col2:
            st.markdown("<h2 style='text-align:center;'>🔐 GEO-TECH LOGIN</h2>", unsafe_allow_html=True)
            user = st.text_input("👤 ID Pengguna")
            pw = st.text_input("🔑 Kata Laluan", type="password")
            if st.button("MASUK", use_container_width=True):
                if user in ["admin123", "admin124", "admin125"] and pw == "123456":
                    st.session_state.logged_in = True
                    st.session_state.intro_done = False 
                    st.rerun()
                else: st.error("ID atau Kata Laluan Salah!")
        return False
    return True

# ==========================================
# --- 4. ALIRAN UTAMA ---
# ==========================================
if semak_login():
    video_data = get_video_base64("PROM.mp4")
    if video_data: video_healing_intro(video_data)

    st.markdown(f"""
        <div style="width: 100%; height: 200px; overflow: hidden; border-radius: 20px; margin-bottom: 20px; display: flex; justify-content: center; align-items: center; background: black; border-bottom: 4px solid #ffcc00;">
            <video autoplay muted loop playsinline style="width: 100%; object-fit: cover; opacity: 0.5;">
                <source src="data:video/mp4;base64,{video_data if video_data else ''}" type="video/mp4">
            </video>
            <h1 style="position: absolute; color: white; text-shadow: 2px 2px 10px black;">🛰️ PUO WEB-GIS PRO</h1>
        </div>
    """, unsafe_allow_html=True)

    # --- SIDEBAR ---
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/ms/thumb/0/05/Logo_PUO.png/200px-Logo_PUO.png", width=100)
    on_off_satelit = st.sidebar.radio("🗺️ Peta Dasar", ["Satelit (Google)", "Standard (OSM)"])
    on_off_bearing = st.sidebar.checkbox("📏 Papar Bearing/Jarak", value=True)
    on_off_label = st.sidebar.checkbox("🏷️ Papar Label Stesen", value=True) # KEMBALIKAN BUTANG INI
    epsg_input = st.sidebar.text_input("🌍 EPSG", value="4390")

    uploaded_file = st.file_uploader("📂 Muat naik CSV (STN, E, N)", type=["csv"])

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        try:
            gdf_raw = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.E, df.N), crs=f"EPSG:{epsg_input}")
            gdf_wgs84 = gdf_raw.to_crs(epsg="4326")
            df['lat'], df['lon'] = gdf_wgs84.geometry.y, gdf_wgs84.geometry.x

            tab1, tab2 = st.tabs(["📊 Peta Interaktif", "📥 Eksport GIS"])

            with tab1:
                st.metric("Keluasan (m²)", f"{kira_luas(df['E'].values, df['N'].values):.3f}")
                m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=19, max_zoom=22)
                
                if on_off_satelit == "Satelit (Google)":
                    folium.TileLayer(
                        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
                        attr="Google", name="Google Satellite", max_zoom=22, max_native_zoom=18
                    ).add_to(m)
                
                # Poligon Lot
                folium.Polygon(locations=list(zip(df.lat, df.lon)), color="yellow", weight=3, fill=True, fill_opacity=0.1).add_to(m)
                
                # Plotting Bearing & Jarak (Selari dengan garisan)
                if on_off_bearing:
                    for i in range(len(df)):
                        p1_e, p1_n = df.iloc[i]['E'], df.iloc[i]['N']
                        p2_e, p2_n = df.iloc[(i+1)%len(df)]['E'], df.iloc[(i+1)%len(df)]['N']
                        
                        b_text, d_val, rot = kira_bearing_jarak((p1_e, p1_n), (p2_e, p2_n))
                        
                        mid_lat = (df.iloc[i]['lat'] + df.iloc[(i+1)%len(df)]['lat']) / 2
                        mid_lon = (df.iloc[i]['lon'] + df.iloc[(i+1)%len(df)]['lon']) / 2
                        
                        folium.Marker(
                            location=[mid_lat, mid_lon],
                            icon=folium.DivIcon(html=f"""
                                <div style="transform: rotate({rot}deg); text-align: center; width: 120px; margin-left: -60px;">
                                    <span style="color: #00FFFF; font-size: 8pt; font-weight: bold; text-shadow: 1px 1px 2px black;">
                                        {b_text}<br>{d_val:.2f}m
                                    </span>
                                </div>""")
                        ).add_to(m)

                # Marker Stesen
                for i, row in df.iterrows():
                    folium.CircleMarker([row.lat, row.lon], radius=4, color="red", fill=True).add_to(m)
                    if on_off_label: # Logik butang on/off stesen
                        folium.Marker(
                            [row.lat, row.lon], 
                            icon=folium.DivIcon(html=f'<div style="color:white; font-size:9pt; font-weight:bold; background:rgba(128,0,0,0.7); padding:1px 4px; border-radius:4px; margin-top:-20px;">{int(row.STN)}</div>')
                        ).add_to(m)
                
                Fullscreen().add_to(m); MeasureControl().add_to(m)
                st_folium(m, width=1200, height=600)

            with tab2:
                # Eksport logic
                gdf_poly = gpd.GeoDataFrame({'unsur': ['Lot'], 'geometry': [Polygon(list(zip(df.E, df.N)))]}, crs=f"EPSG:{epsg_input}")
                st.download_button("🗺️ Muat Turun GeoJSON", data=gdf_poly.to_json(), file_name="puo_lot.geojson")

        except Exception as e: st.error(f"⚠️ Ralat: {e}")
