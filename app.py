import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine

# 1. Configuración inicial (Siempre va primero)
st.set_page_config(page_title="Análisis Operativo - MetadataSur", layout="wide")

# --- 2. EL PATOVICA (SISTEMA DE LOGIN) VA ACÁ ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔒 Acceso a MetadataSur - Análisis")
    st.markdown("Por favor, ingresá tus credenciales para ver el dashboard operativo.")
    
    usuario = st.text_input("Usuario")
    clave = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar"):
        if usuario == "selma_admin" and clave == "selma2026":
            st.session_state.autenticado = True
            st.rerun() # Si está bien, recarga la página y salta este bloque
        else:
            st.error("Usuario o contraseña incorrectos")
            
    # OJO: Este st.stop() tiene que estar a esta altura, fuera del if del botón
    st.stop() 
# ------------------------------------------------

# --- 3. RECIÉN ACÁ EMPIEZA LA CONEXIÓN A DATOS Y EL DASHBOARD ---
# Todo este código de abajo SOLO se va a leer si el cliente puso bien la clave 
# y la variable 'autenticado' pasó a ser True.

@st.cache_data(ttl=600)
def load_data():
    URL_NEON = "postgresql://neondb_owner:npg_S0DXeQT4KYCl@ep-fragrant-water-aigaxh2j-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require"
    engine = create_engine(URL_NEON)
    # ... tu consulta SQL ...
    
# ... (el resto de tu código: filtros, KPIs y gráficos) ...
