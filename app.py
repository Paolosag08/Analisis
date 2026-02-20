import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine

# 1. Configuración de la página
st.set_page_config(page_title="Análisis Operativo - MetadataSur", layout="wide")

# 2. Conexión a Neon y carga de datos (con caché para que vuele)
@st.cache_data(ttl=600) # Se actualiza cada 10 minutos
def load_data():
    # Tu conexión a Neon
    URL_NEON = "postgresql://neondb_owner:npg_S0DXeQT4KYCl@ep-fragrant-water-aigaxh2j-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require"
    engine = create_engine(URL_NEON)
    
    # Traemos los datos de la tabla que acabas de crear
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

# Convertimos las fechas para el filtro
df['fecha_emision'] = pd.to_datetime(df['fecha_emision'])
fecha_min, fecha_max = df['fecha_emision'].min().date(), df['fecha_emision'].max().date()
fechas_seleccionadas = st.sidebar.date_input("Rango de Fechas", [fecha_min, fecha_max], min_value=fecha_min, max_value=fecha_max)

# Filtro de Sector
sectores = df['sector_emision'].dropna().unique().tolist()
sector_seleccionado = st.sidebar.multiselect("Sector", options=sectores, default=sectores)

# Aplicar filtros
if len(fechas_seleccionadas) == 2:
    mask = (df['fecha_emision'].dt.date >= fechas_seleccionadas[0]) & (df['fecha_emision'].dt.date <= fechas_seleccionadas[1]) & (df['sector_emision'].isin(sector_seleccionado))
    df_filtrado = df[mask]
else:
    df_filtrado = df[df['sector_emision'].isin(sector_seleccionado)]

# 4. Título Principal
st.title("📊 Análisis Operativo de Turnos")
st.markdown(f"**Sucursal:** ANT | **Periodo Seleccionado:** {fechas_seleccionadas[0]} al {fechas_seleccionadas[-1] if len(fechas_seleccionadas)>1 else fechas_seleccionadas[0]}")
st.divider()

# 5. KPIs y Gráficos
if not df_filtrado.empty:
    total_turnos = len(df_filtrado)
    abandonos = len(df_filtrado[df_filtrado['estado'].isin(['NO ATENDIDO', 'CANCELADO'])])
    tasa_abandono = (abandonos / total_turnos) * 100 if total_turnos > 0 else 0
    tme = df_filtrado['tiempo_espera_seg'].mean() / 60
    tma = df_filtrado['tiempo_atencion_seg'].mean() / 60

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
        espera_sector = df_filtrado.groupby('sector_emision')['tiempo_espera_seg'].mean().reset_index()
        espera_sector['minutos'] = espera_sector['tiempo_espera_seg'] / 60
        espera_sector = espera_sector.sort_values(by='minutos')
        fig_espera = px.bar(espera_sector, x='minutos', y='sector_emision', orientation='h',
                            color='minutos', color_continuous_scale='Reds')
        st.plotly_chart(fig_espera, use_container_width=True)

    with row1_col2:
        st.subheader("Estado Final de Atención")
        estado_turnos = df_filtrado['estado'].value_counts().reset_index()
        estado_turnos.columns = ['Estado', 'Cantidad']
        fig_estado = px.pie(estado_turnos, names='Estado', values='Cantidad', hole=0.4,
                            color='Estado', color_discrete_map={'ATENDIDO': '#2ca02c', 'NO ATENDIDO': '#d62728', 'CANCELADO': '#7f7f7f'})
        st.plotly_chart(fig_estado, use_container_width=True)

else:
    st.warning("No hay datos para los filtros seleccionados.")
