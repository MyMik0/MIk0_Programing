import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point
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
            # Shapefile tidak suka mixed geometry, jadi kita simpan sebagai GeoJSON dalam ZIP 
            # atau simpan fail utama. Untuk kegunaan GIS, GeoJSON lebih fleksibel.
            path = os.path.join(temp_dir, "data_traves_puo.shp")
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
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st.markdown("""<div style='text-align:center;'><h3>🔐 Log Masuk PUO Geomatik</h3></div>""", unsafe_allow_html=True)
            user = st.text_input("ID Pengguna")
            pw = st.text_input("Kata Laluan", type="password")
            if st.button("Masuk Sekarang", use_container_width=True):
                if (user == "admin123" or user == "admin124" or user == "admin125") and pw == "123456":
                    st.session_state.logged_in = True
                    st.session_state.current_user = user
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
    video_data = get_video_base64("PROM.mp4")
    
    if video_data:
        video_healing_intro(video_data)

    st.markdown(f"""
        <style>
        .header-box {{
            position: relative; width: 100%; height: 280px;
            overflow: hidden; border-radius: 25px; margin-bottom: 30px;
            display: flex; justify-content: center; align-items: center;
            border-bottom: 5px solid #ffcc00; box-shadow: 0 15px 35px rgba(0,0,0,0.4);
        }}
        .header-video {{
            position: absolute; top: 50%; left: 50%;
            min-width: 100%; min-height: 100%; z-index: 0;
            transform: translate(-50%, -50%); filter: brightness(40%); object-fit: cover;
        }}
        .header-content {{ position: relative; z-index: 1; color: white; text-align: center; }}
        .header-signature {{
            position: absolute; bottom: 15px; right: 25px; z-index: 2;
            color: white; font-family: 'Courier New', monospace; font-size: 0.9rem;
            opacity: 0.7;
        }}
        </style>
        <div class="header-box">
            <video autoplay muted loop playsinline class="header-video">
                <source src="data:video/mp4;base64,{video_data if video_data else ''}" type="video/mp4">
            </video>
            <div class="header-content">
                <h1 style='font-size: 3rem;'>🛰️ PUO WEB-GIS PRO-PLOTTER</h1>
                <p>Precision Mapping Experience</p>
            </div>
            <div class="header-signature">Developed by: <b>AHMAD ILHAM</b></div>
        </div>
    """, unsafe_allow_html=True)

    st.sidebar.image("https://upload.wikimedia.org/wikipedia/ms/thumb/0/05/Logo_PUO.png/200px-Logo_PUO.png", width=150)
    st.sidebar.write(f"👤 User: **{st.session_state.get('current_user', 'Admin')}**")
    st.sidebar.header("⚙️ Konfigurasi")
    on_off_satelit = st.sidebar.radio("🗺️ Jenis Peta", ["Satelit (Google)", "Standard (OSM)"])
    on_off_bearing = st.sidebar.checkbox("📏 Papar Bearing/Jarak", value=True)
    on_off_label = st.sidebar.checkbox("🏷️ Papar Label Stesen", value=True)
    epsg_input = st.sidebar.text_input("🌍 Kod EPSG", value="4390")
    
    if st.sidebar.button("Keluar Sistem"):
        st.session_state.logged_in = False
        st.session_state.intro_done = False
        st.rerun()

    uploaded_file = st.file_uploader("📂 Muat naik fail CSV", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        try:
            gdf_raw = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.E, df.N), crs=f"EPSG:{epsg_input}")
            gdf_wgs84 = gdf_raw.to_crs(epsg="4326")
            df['lat'], df['lon'] = gdf_wgs84.geometry.y, gdf_wgs84.geometry.x
            
            tab1, tab2 = st.tabs(["📊 Visualisasi Peta", "📥 Eksport Data GIS"])
            
            with tab1:
                st.metric("Luas (m²)", f"{kira_luas(df['E'].values, df['N'].values):.3f}")
                center = [df['lat'].mean(), df['lon'].mean()]
                m = folium.Map(location=center, zoom_start=19)
                
                if on_off_satelit == "Satelit (Google)":
                    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Google Satellite').add_to(m)

                # Lukis Poligon
                coords = list(zip(df.lat, df.lon))
                folium.Polygon(locations=coords, color="yellow", weight=3, fill=True, fill_opacity=0.2).add_to(m)

                # Marker & Label
                for i, row in df.iterrows():
                    if on_off_label:
                        folium.Marker([row.lat, row.lon], icon=folium.DivIcon(html=f'<div style="color:white; background:rgba(128,0,0,0.7); padding:2px 5px; border-radius:3px; font-size:9pt;">{int(row.STN)}</div>')).add_to(m)
                    folium.CircleMarker([row.lat, row.lon], radius=3, color="red", fill=True).add_to(m)

                # Bearing & Jarak
                if on_off_bearing:
                    for i in range(len(df)):
                        p1, p2 = (df.iloc[i]['E'], df.iloc[i]['N']), (df.iloc[(i + 1) % len(df)]['E'], df.iloc[(i + 1) % len(df)]['N'])
                        b_text, d_val, _ = kira_bearing_jarak(p1, p2)
                        mid_lat = (df.iloc[i]['lat'] + df.iloc[(i + 1) % len(df)]['lat']) / 2
                        mid_lon = (df.iloc[i]['lon'] + df.iloc[(i + 1) % len(df)]['lon']) / 2
                        folium.Marker([mid_lat, mid_lon], icon=folium.DivIcon(html=f'<div style="color:#00ffff; font-weight:bold; font-size:8pt; text-shadow: 1px 1px black;">{b_text}<br>{d_val:.2f}m</div>')).add_to(m)

                Fullscreen().add_to(m)
                MeasureControl().add_to(m)
                st_folium(m, width="100%", height=600)

            with tab2:
                st.subheader("📥 Muat Turun Data Geometrik Lengkap")
                
                # 1. Lapisan Poligon
                gdf_poly = gpd.GeoDataFrame({'Feature': ['Lot Tanah'], 'geometry': [Polygon(list(zip(df.E, df.N)))]}, crs=f"EPSG:{epsg_input}")
                
                # 2. Lapisan Stesen (Points)
                gdf_pts = gpd.GeoDataFrame(df[['STN', 'E', 'N']], geometry=gpd.points_from_xy(df.E, df.N), crs=f"EPSG:{epsg_input}")
                
                # 3. Lapisan Garisan (Lines) dengan Bearing/Jarak
                lines_list = []
                for i in range(len(df)):
                    p1, p2 = (df.iloc[i]['E'], df.iloc[i]['N']), (df.iloc[(i + 1) % len(df)]['E'], df.iloc[(i + 1) % len(df)]['N'])
                    b_text, d_val, _ = kira_bearing_jarak(p1, p2)
                    lines_list.append({
                        'geometry': LineString([p1, p2]),
                        'Bearing': b_text,
                        'Jarak_m': round(d_val, 3),
                        'Dari_STN': int(df.iloc[i]['STN']),
                        'Ke_STN': int(df.iloc[(i + 1) % len(df)]['STN'])
                    })
                gdf_lines = gpd.GeoDataFrame(lines_list, crs=f"EPSG:{epsg_input}")

                # Gabungkan semua ke dalam satu GeoJSON (GeoJSON menyokong mixed types)
                gdf_combined = pd.concat([gdf_poly, gdf_pts, gdf_lines], ignore_index=True)
                
                st.write("Klik butang di bawah untuk eksport fail:")
                st.download_button("🛰️ Eksport ke GeoJSON (Lengkap)", data=gdf_combined.to_json(), file_name="PUO_WebGIS_Complete.geojson", use_container_width=True)
                
                # Eksport Shapefile (Hanya Poligon untuk kestabilan format .shp)
                shp_zip = create_shapefile_zip(gdf_poly)
                if shp_zip:
                    st.download_button("📁 Eksport Shapefile Poligon (ZIP)", data=shp_zip, file_name="PUO_Lot_Shapefile.zip", use_container_width=True)
                
                st.success("Nota: Fail GeoJSON mengandungi data stesen, garisan traves, bearing, dan jarak yang boleh dibuka dalam QGIS/AutoCAD.")

        except Exception as e:
            st.error(f"Ralat Pemprosesan: {e}")
