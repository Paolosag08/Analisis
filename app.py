import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine

# 1. Configuración de la página
st.set_page_config(page_title="Análisis Operativo - MetadataSur", layout="wide")

# 2. Conexión a Neon y carga de datos
@st.cache_data(ttl=600) # Se actualiza cada 10 minutos
def load_data():
    URL_NEON = "postgresql://neondb_owner:npg_S0DXeQT4KYCl@ep-fragrant-water-aigaxh2j-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require"
    engine = create_engine(URL_NEON)
    
    # Traemos los datos. Pandas respetará los nombres originales: 'Fecha Emisión', 'Sector', etc.
    query = "SELECT * FROM turnos_historico"
    df = pd.read_sql(query, engine)
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Error al conectar con la base de datos: {e}")
    st.stop()

# 3. Interfaz y Filtros
st.sidebar.title("Filtros Globales")

# --- NUEVO: Filtro de Sucursales ---
# Extraemos todas las sucursales únicas que existen en tu base de datos de Neon
sucursales_disponibles = df['Sucursal'].dropna().unique().tolist()

# Creamos un selector múltiple en la barra lateral
sucursales_seleccionadas = st.sidebar.multiselect(
    "Seleccionar Sucursal", 
    options=sucursales_disponibles, 
    default=sucursales_disponibles # Por defecto muestra todas
)

# Convertimos las fechas para el filtro
df['Fecha Emisión'] = pd.to_datetime(df['Fecha Emisión'])
fecha_min, fecha_max = df['Fecha Emisión'].min().date(), df['Fecha Emisión'].max().date()
fechas_seleccionadas = st.sidebar.date_input("Rango de Fechas", [fecha_min, fecha_max], min_value=fecha_min, max_value=fecha_max)

# Filtro de Sector
sectores = df['Sector'].dropna().unique().tolist()
sector_seleccionado = st.sidebar.multiselect("Sector", options=sectores, default=sectores)

# --- NUEVO: Aplicar TODOS los filtros juntos ---
# Verificamos que se hayan seleccionado fechas de inicio y fin
if len(fechas_seleccionadas) == 2:
    mask = (
        (df['Fecha Emisión'].dt.date >= fechas_seleccionadas[0]) & 
        (df['Fecha Emisión'].dt.date <= fechas_seleccionadas[1]) & 
        (df['Sector'].isin(sector_seleccionado)) & 
        (df['Sucursal'].isin(sucursales_seleccionadas)) # Acá filtramos la sucursal
    )
    df_filtrado = df[mask]
else:
    df_filtrado = df[(df['Sector'].isin(sector_seleccionado)) & (df['Sucursal'].isin(sucursales_seleccionadas))]

# 4. Título Principal Dinámico
st.title("📊 Análisis Operativo de Turnos")
# Mostramos en el título qué sucursales se están viendo
nombres_sucursales = ", ".join(sucursales_seleccionadas) if sucursales_seleccionadas else "Ninguna"
st.markdown(f"**Sucursales analizadas:** {nombres_sucursales} | **Periodo:** {fechas_seleccionadas[0]} al {fechas_seleccionadas[-1] if len(fechas_seleccionadas)>1 else fechas_seleccionadas[0]}")
st.divider()

# 5. KPIs y Gráficos
if not df_filtrado.empty:
    total_turnos = len(df_filtrado)
    abandonos = len(df_filtrado[df_filtrado['Estado'].isin(['NO ATENDIDO', 'CANCELADO'])])
    tasa_abandono = (abandonos / total_turnos) * 100 if total_turnos > 0 else 0
    
    # Usamos las columnas de minutos que ya se habían calculado al subir a Neon
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
