import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon
import folium
from folium.plugins import MeasureControl, Fullscreen
from streamlit_folium import st_folium
import io
import zipfile
import tempfile
import os

# ==========================================
# --- 1. FUNGSI MATEMATIK & GEOMATIK ---
# ==========================================

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

def create_shapefile_zip(gdf):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_name = "poligon_gis_puo"
            path = os.path.join(temp_dir, f"{base_name}.shp")
            gdf.to_file(path, engine="pyogrio") 
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        zip_file.write(os.path.join(root, file), arcname=file)
            return zip_buffer.getvalue()
    except Exception as e:
        st.error(f"Ralat Eksport GIS: {e}")
        return None

# ==========================================
# --- 2. SISTEM LOG MASUK ---
# ==========================================

def semak_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.set_page_config(page_title="Log Masuk | PUO Geomatik", page_icon="🔐")
        st.markdown("""
            <style>
            .login-box {
                background-color: #f9f9f9;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                text-align: center;
            }
            </style>
        """, unsafe_allow_html=True)
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            st.image("https://upload.wikimedia.org/wikipedia/ms/thumb/0/05/Logo_PUO.png/200px-Logo_PUO.png", width=100)
            st.subheader("🔐 Log Masuk PUO Geomatik")
            user = st.text_input("ID Pengguna")
            pw = st.text_input("Kata Laluan", type="password")
            if st.button("Masuk Sekarang", use_container_width=True):
                if user == "admin123" and pw == "123456":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("ID atau Kata Laluan Salah!")
            st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

# ==========================================
# --- 3. APLIKASI UTAMA (WEB-GIS) ---
# ==========================================

if semak_login():
    try:
        st.set_page_config(page_title="PUO Geomatik - WebGIS Pro", layout="wide")
    except:
        pass

    # HEADER VISUAL HEALING & CSS PERBAIKAN TEKS LUAS
    st.markdown("""
        <style>
        .main-header {
            background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
            padding: 30px;
            border-radius: 20px;
            color: white;
            text-align: center;
            margin-bottom: 25px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
            border-bottom: 4px solid #ffcc00;
        }
        /* GELAPKAN TEKS KELUASAN (METRIC) */
        [data-testid="stMetricLabel"] {
            color: #333333 !important; /* Warna label kelabu gelap */
            font-weight: bold !important;
        }
        [data-testid="stMetricValue"] {
            color: #1e3c72 !important; /* Warna nilai biru gelap */
            font-weight: 800 !important;
        }
        .stMetric {
            background: #ffffff;
            padding: 15px;
            border-radius: 12px;
            border: 1px solid #d1d8e0;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
        }
        </style>
        <div class="main-header">
            <h1 style='margin:0; letter-spacing: 2px;'>🛰️ PUO WEB-GIS PRO-PLOTTER</h1>
            <p style='margin:0; opacity: 0.8; font-style: italic;'>Precision Mapping & Visual Healing Experience</p>
        </div>
    """, unsafe_allow_html=True)

    # SIDEBAR KONTROL
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/ms/thumb/0/05/Logo_PUO.png/200px-Logo_PUO.png", width=150)
    st.sidebar.divider()
    st.sidebar.header("⚙️ Tetapan Lapisan")
    on_off_satelit = st.sidebar.radio("🗺️ Jenis Peta", ["Satelit (Google Hybrid)", "Peta Standard (OSM)"])
    on_off_bearing = st.sidebar.checkbox("📏 Papar Bearing & Jarak", value=True)
    on_off_label = st.sidebar.checkbox("🏷️ Papar Label Stesen", value=True)
    epsg_input = st.sidebar.text_input("🌍 Kod EPSG (Contoh: 4390)", value="4390")
    
    if st.sidebar.button("Keluar Sistem"):
        st.session_state.logged_in = False
        st.rerun()

    uploaded_file = st.file_uploader("📂 Muat naik fail CSV Koordinat (STN, E, N)", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        
        try:
            gdf_raw = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.E, df.N), crs=f"EPSG:{epsg_input}")
            gdf_wgs84 = gdf_raw.to_crs(epsg="4326")
            df['lat'] = gdf_wgs84.geometry.y
            df['lon'] = gdf_wgs84.geometry.x

            tab1, tab2 = st.tabs(["📊 Paparan Peta Interaktif", "📥 Eksport Data GIS"])

            with tab1:
                # Paparan Keluasan yang telah digelapkan
                luas = kira_luas(df['E'].values, df['N'].values)
                st.metric("Keluasan Poligon (m²)", f"{luas:.3f}")

                center_lat, center_lon = df['lat'].mean(), df['lon'].mean()
                google_hybrid = "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}"
                
                if on_off_satelit == "Satelit (Google Hybrid)":
                    m = folium.Map(location=[center_lat, center_lon], zoom_start=22, max_zoom=22, tiles=google_hybrid, attr="Google")
                else:
                    m = folium.Map(location=[center_lat, center_lon], zoom_start=20, max_zoom=22)

                Fullscreen().add_to(m)
                MeasureControl(position='topleft', primary_length_unit='meters').add_to(m)

                coords = list(zip(df.lat, df.lon))
                folium.Polygon(locations=coords, color="yellow", weight=3, fill=True, fill_opacity=0.25).add_to(m)
                m.fit_bounds(coords, max_zoom=22)

                if on_off_bearing:
                    for i in range(len(df)):
                        p1 = (df.iloc[i]['E'], df.iloc[i]['N'])
                        p2 = (df.iloc[(i + 1) % len(df)]['E'], df.iloc[(i + 1) % len(df)]['N'])
                        b_text, d_val, b_deg = kira_bearing_jarak(p1, p2)
                        mid_lat = (df.iloc[i]['lat'] + df.iloc[(i + 1) % len(df)]['lat']) / 2
                        mid_lon = (df.iloc[i]['lon'] + df.iloc[(i + 1) % len(df)]['lon']) / 2
                        
                        display_angle = b_deg - 90
                        if 90 < b_deg < 270:
                            display_angle += 180

                        folium.Marker(
                            location=[mid_lat, mid_lon],
                            icon=folium.DivIcon(html=f"""
                                <div style="
                                    transform: rotate({display_angle}deg); 
                                    white-space: nowrap;
                                    text-align: center;
                                    width: 120px;
                                    margin-left: -60px;
                                    font-size: 8.5pt; 
                                    color: #00FFFF; 
                                    font-weight: bold; 
                                    text-shadow: 2px 2px 4px #000;">
                                    {b_text}<br>{d_val:.2f}m
                                </div>""")
                        ).add_to(m)

                for i, row in df.iterrows():
                    if on_off_label:
                        folium.Marker(
                            location=[row.lat, row.lon],
                            icon=folium.DivIcon(html=f"""<div style="color: white; background: rgba(0,0,0,0.7); padding: 2px 6px; border-radius: 5px; font-size: 10px; border: 1px solid #ffcc00; min-width:20px; text-align:center;"><b>{int(row.STN)}</b></div>"""),
                        ).add_to(m)
                    folium.CircleMarker(location=[row.lat, row.lon], radius=4, color="red", fill=True, fill_color="white", fill_opacity=1).add_to(m)

                st_folium(m, width=1200, height=650, key="main_map_pro")

            with tab2:
                st.subheader("📥 Muat Turun Data")
                geom = Polygon(list(zip(df.E, df.N)))
                gdf_export = gpd.GeoDataFrame(index=[0], geometry=[geom], crs=f"EPSG:{epsg_input}")
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("🗺️ Muat Turun GeoJSON", data=gdf_export.to_json(), file_name="poligon_puo.geojson")
                with c2:
                    shp_zip = create_shapefile_zip(gdf_export)
                    if shp_zip:
                        st.download_button("📁 Muat Turun Shapefile (ZIP)", data=shp_zip, file_name="poligon_puo_shp.zip")

        except Exception as e:
            st.error(f"⚠️ Ralat: {e}")
    else:
        st.info("💡 Sila muat naik fail CSV koordinat.")
