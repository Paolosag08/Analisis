import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA (Siempre primero)
# ==========================================
st.set_page_config(page_title="Análisis Operativo - MetadataSur", layout="wide")

# ==========================================
# 2. SISTEMA DE LOGIN (El "Patovica")
# ==========================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔒 Acceso a MetadataSur - Análisis")
    st.markdown("Por favor, ingresá tus credenciales para ver el dashboard operativo.")
    
    usuario = st.text_input("Usuario")
    clave = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar"):
        # Credenciales de prueba para tu primer cliente
        if usuario == "selma_admin" and clave == "selma2026":
            st.session_state.autenticado = True
            st.rerun() # Recarga la página y deja pasar al código de abajo
        else:
            st.error("Usuario o contraseña incorrectos")
            
    # ST.STOP() ES VITAL ACÁ: Frena la lectura del código si no estás autenticado
    st.stop() 

# ==========================================
# 3. CONEXIÓN A LA BASE DE DATOS (NEON)
# ==========================================
@st.cache_data(ttl=600) # Se actualiza cada 10 minutos
def load_data():
    URL_NEON = "postgresql://neondb_owner:npg_S0DXeQT4KYCl@ep-fragrant-water-aigaxh2j-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require"
    engine = create_engine(URL_NEON)
    
    # Traemos los turnos y los unimos con las tablas de sucursales y empresas
    query = """
    SELECT 
        t.*, 
        s.nombre_sucursal, 
        e.nombre_empresa 
    FROM turnos_historico t
    LEFT JOIN sucursales s ON t."Sucursal" = s.sigla
    LEFT JOIN empresas e ON s.id_empresa = e.id_empresa
    """
    df = pd.read_sql(query, engine)
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Error al conectar con la base de datos: {e}")
    st.stop()

# ==========================================
# 4. INTERFAZ Y FILTROS (BARRA LATERAL)
# ==========================================
st.sidebar.title("Filtros Globales")

# --- FILTRO 1: EMPRESA ---
empresas_disponibles = df['nombre_empresa'].dropna().unique().tolist()
if not empresas_disponibles:
    st.warning("No se encontraron empresas. Asegúrate de haber corrido el script de jerarquía.")
    st.stop()
    
empresa_seleccionada = st.sidebar.selectbox("Empresa", options=empresas_disponibles)

# Filtramos temporalmente para saber qué sucursales tiene esta empresa
df_empresa = df[df['nombre_empresa'] == empresa_seleccionada]

# --- FILTRO 2: SUCURSALES ---
sucursales_disponibles = df_empresa['nombre_sucursal'].dropna().unique().tolist()
sucursales_seleccionadas = st.sidebar.multiselect("Sucursales", options=sucursales_disponibles, default=sucursales_disponibles)

# --- FILTRO 3: FECHAS Y SECTORES ---
df['Fecha Emisión'] = pd.to_datetime(df['Fecha Emisión'])
fecha_min, fecha_max = df['Fecha Emisión'].min().date(), df['Fecha Emisión'].max().date()
fechas_seleccionadas = st.sidebar.date_input("Rango de Fechas", [fecha_min, fecha_max], min_value=fecha_min, max_value=fecha_max)

sectores_disponibles = df_empresa['Sector'].dropna().unique().tolist()
sector_seleccionado = st.sidebar.multiselect("Sector", options=sectores_disponibles, default=sectores_disponibles)

# ==========================================
# 5. APLICAR FILTROS A LOS DATOS
# ==========================================
if len(fechas_seleccionadas) == 2:
    mask = (
        (df['nombre_empresa'] == empresa_seleccionada) &
        (df['nombre_sucursal'].isin(sucursales_seleccionadas)) &
        (df['Sector'].isin(sector_seleccionado)) &
        (df['Fecha Emisión'].dt.date >= fechas_seleccionadas[0]) &
        (df['Fecha Emisión'].dt.date <= fechas_seleccionadas[1])
    )
    df_filtrado = df[mask]
else:
    df_filtrado = df[
        (df['nombre_empresa'] == empresa_seleccionada) &
        (df['nombre_sucursal'].isin(sucursales_seleccionadas)) &
        (df['Sector'].isin(sector_seleccionado))
    ]

# ==========================================
# 6. TÍTULO PRINCIPAL DEL DASHBOARD
# ==========================================
st.title("📊 Análisis Operativo de Turnos")
st.markdown(f"**Empresa:** {empresa_seleccionada} | **Sucursales:** {', '.join(sucursales_seleccionadas) if sucursales_seleccionadas else 'Ninguna'} | **Periodo:** {fechas_seleccionadas[0]} al {fechas_seleccionadas[-1] if len(fechas_seleccionadas)>1 else fechas_seleccionadas[0]}")
st.divider()

# ==========================================
# 7. KPIs Y GRÁFICOS
# ==========================================
if not df_filtrado.empty:
    total_turnos = len(df_filtrado)
    abandonos = len(df_filtrado[df_filtrado['Estado'].isin(['NO ATENDIDO', 'CANCELADO'])])
    tasa_abandono = (abandonos / total_turnos) * 100 if total_turnos > 0 else 0
    tme = df_filtrado['Espera_Minutos'].mean()
    tma = df_filtrado['Atencion_Minutos'].mean()

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Volumen Total", f"{total_turnos:,}".replace(',', '.'))
    col2.metric("Tasa de Abandono", f"{tasa_abandono:.1f} %", delta=f"{abandonos} turnos perdidos", delta_color="inverse")
    col3.metric("Tiempo Medio Espera", f"{tme:.1f} min")
    col4.metric("Tiempo Medio Atención", f"{tma:.1f} min")
    st.divider()

    # Gráficos
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        st.subheader("Tiempo de Espera por Sector")
        espera_sector = df_filtrado.groupby('Sector')['Espera_Minutos'].mean().reset_index()
        espera_sector = espera_sector.sort_values(by='Espera_Minutos')
        fig_espera = px.bar(espera_sector, x='Espera_Minutos', y='Sector', orientation='h',
                            color='Espera_Minutos', color_continuous_scale='Reds',
                            labels={'Espera_Minutos': 'Minutos', 'Sector': 'Sector'})
        st.plotly_chart(fig_espera, use_container_width=True)

    with row1_col2:
        st.subheader("Estado Final de Atención")
        estado_turnos = df_filtrado['Estado'].value_counts().reset_index()
        estado_turnos.columns = ['Estado', 'Cantidad']
        fig_estado = px.pie(estado_turnos, names='Estado', values='Cantidad', hole=0.4,
                            color='Estado', color_discrete_map={'ATENDIDO': '#2ca02c', 'NO ATENDIDO': '#d62728', 'CANCELADO': '#7f7f7f'})
        st.plotly_chart(fig_estado, use_container_width=True)

else:
    st.warning("No hay datos para los filtros seleccionados.")
