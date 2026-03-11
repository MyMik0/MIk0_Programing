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
            path = os.path.join(temp_dir, "data_geomatik_puo.shp")
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
            st.markdown("<h2 style='text-align:center; color:#800000;'>GEO-TECH PRO</h2>", unsafe_allow_html=True)
            user = st.text_input("👤 ID Pengguna")
            pw = st.text_input("🔑 Kata Laluan", type="password")
            if st.button("PENGESAHAN MASUK", use_container_width=True):
                if user in ["admin123", "admin124", "admin125"] and pw == "123456":
                    st.session_state.logged_in = True
                    st.session_state.intro_done = False 
                    st.session_state.current_user = user 
                    st.rerun()
                else: st.error("ID atau Kata Laluan Tidak Sah!")
        return False
    return True

# ==========================================
# --- 4. ALIRAN UTAMA ---
# ==========================================
if semak_login():
    video_data = get_video_base64("PROM.mp4")
    if video_data: video_healing_intro(video_data)

    st.markdown(f"""
        <div style="width: 100%; height: 280px; overflow: hidden; border-radius: 25px; background: black; position: relative; border-bottom: 5px solid #ffcc00; display: flex; align-items: center; justify-content: center;">
            <video autoplay muted loop playsinline style="width: 100%; opacity: 0.4; object-fit: cover;">
                <source src="data:video/mp4;base64,{video_data if video_data else ''}" type="video/mp4">
            </video>
            <div style="position: absolute; color: white; text-align: center;">
                <h1 style='font-size: 3.5rem; margin: 0;'>🛰️ PUO WEB-GIS PRO-PLOTTER</h1>
                <p>Advanced Precision Solution | Developed by: <b>AHMAD ILHAM</b></p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.sidebar.image("https://upload.wikimedia.org/wikipedia/ms/thumb/0/05/Logo_PUO.png/200px-Logo_PUO.png", width=150)
    st.sidebar.write(f"👤 Pengguna: **{st.session_state.get('current_user', 'User')}**")
    on_off_satelit = st.sidebar.radio("🗺️ Jenis Peta", ["Satelit (Google)", "Standard (OSM)"])
    on_off_bearing = st.sidebar.checkbox("📏 Papar Bearing/Jarak", value=True)
    on_off_label = st.sidebar.checkbox("🏷️ Papar Label Stesen", value=True)
    epsg_input = st.sidebar.text_input("🌍 Kod EPSG", value="4390")

    uploaded_file = st.file_uploader("📂 Muat naik fail CSV (Format: STN, E, N)", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        try:
            gdf_raw = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.E, df.N), crs=f"EPSG:{epsg_input}")
            gdf_wgs84 = gdf_raw.to_crs(epsg="4326")
            df['lat'], df['lon'] = gdf_wgs84.geometry.y, gdf_wgs84.geometry.x

            tab1, tab2 = st.tabs(["📊 Peta Interaktif", "📥 Eksport GIS"])

            with tab1:
                st.metric("Keluasan Tanah (m²)", f"{kira_luas(df['E'].values, df['N'].values):.3f}")
                center = [df['lat'].mean(), df['lon'].mean()]
                m = folium.Map(location=center, zoom_start=20, max_zoom=22)
                if on_off_satelit == "Satelit (Google)":
                    folium.TileLayer(tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", attr="Google", name="Google Satellite", max_zoom=22).add_to(m)

                coords = list(zip(df.lat, df.lon))
                folium.Polygon(locations=coords, color="yellow", weight=3, fill=True, fill_opacity=0.3).add_to(m)
                
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
                        folium.Marker(location=[row.lat, row.lon], icon=folium.DivIcon(html=f'<div style="color: white; background: rgba(128,0,0,0.8); padding: 2px 5px; border-radius: 5px; font-size: 10px; border: 1px solid #ffcc00;"><b>{int(row.STN)}</b></div>')).add_to(m)
                    folium.CircleMarker(location=[row.lat, row.lon], radius=4, color="red", fill=True).add_to(m)
                
                Fullscreen().add_to(m); MeasureControl().add_to(m)
                st_folium(m, width=1200, height=600)

            with tab2:
                st.subheader("📥 Muat Turun Data Lengkap")
                
                # 1. Bina Poligon
                geom_poly = Polygon(list(zip(df.E, df.N)))
                
                # 2. Bina LineString (Data Garisan)
                line_coords = list(zip(df.E, df.N))
                line_coords.append(line_coords[0]) # Tutup garisan ke stesen asal
                geom_line = LineString(line_coords)
                
                # 3. Sediakan GeoDataFrame Gabungan
                # Points
                gdf_pts = gpd.GeoDataFrame({'STN': df['STN'].astype(int), 'Type': 'Station', 'Luas': 0}, geometry=gpd.points_from_xy(df.E, df.N), crs=f"EPSG:{epsg_input}")
                # Polygon
                gdf_poly = gpd.GeoDataFrame({'STN': [0], 'Type': 'Lot_Area', 'Luas': [round(kira_luas(df['E'].values, df['N'].values), 3)]}, geometry=[geom_poly], crs=f"EPSG:{epsg_input}")
                # Line (Data garisan yang anda minta)
                gdf_line = gpd.GeoDataFrame({'STN': [0], 'Type': 'Boundary_Line', 'Luas': 0}, geometry=[geom_line], crs=f"EPSG:{epsg_input}")
                
                gdf_final = pd.concat([gdf_pts, gdf_poly, gdf_line], ignore_index=True)

                st.write("📋 **Pratonton Atribut (QGIS/CAD Ready):**")
                st.dataframe(gdf_final.drop(columns='geometry').head())
                
                st.download_button("🗺️ Simpan GeoJSON", data=gdf_final.to_json(), file_name="puo_pro_complete.geojson")
                shp_zip = create_shapefile_zip(gdf_final)
                if shp_zip: st.download_button("📁 Simpan Shapefile (ZIP)", data=shp_zip, file_name="puo_shp_pro.zip")

        except Exception as e: st.error(f"⚠️ Ralat: {e}")
