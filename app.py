import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuración de la página
st.set_page_config(page_title="Dashboard Operativo - MetadataSur", layout="wide")

# 2. Función para cargar y limpiar datos (Optimizada con caché de memoria)
@st.cache_data
def load_data():
    # Asegúrate de que el archivo CSV esté en la misma carpeta que app.py
    df = pd.read_csv('Turnos_ANT.xlsx')
    
    # Limpiar nombres de columnas (quitar espacios extra y saltos de línea de tu archivo)
    df.columns = [col.strip().replace('\n', '') for col in df.columns]
    
    # Agregar la jerarquía (simulando la extracción del nombre del archivo 'Turnos_ANT')
    df['Sucursal'] = 'ANT'
    
    # Convertir fechas a formato datetime
    df['Fecha Emisión'] = pd.to_datetime(df['Fecha Emisión'])
    df['Hora'] = df['Fecha Emisión'].dt.hour
    df['Fecha'] = df['Fecha Emisión'].dt.date
    
    # Convertir tiempos (HH:MM:SS) a minutos continuos (float) para calcular promedios
    df['Espera_Minutos'] = pd.to_timedelta(df['Tiempo Espera'], errors='coerce').dt.total_seconds() / 60
    df['Atencion_Minutos'] = pd.to_timedelta(df['Tiempo Atención'], errors='coerce').dt.total_seconds() / 60
    
    return df

try:
    df = load_data()
except FileNotFoundError:
    st.error("Por favor, asegúrate de que el archivo 'Turnos_ANT.xlsx - Sheet1.csv' esté subido en GitHub junto a este script.")
    st.stop()

# 3. Interfaz de Usuario y Filtros (Sidebar)
st.sidebar.title("Filtros Globales")

# Filtro de Fechas
fecha_min, fecha_max = df['Fecha'].min(), df['Fecha'].max()
fechas_seleccionadas = st.sidebar.date_input("Rango de Fechas", [fecha_min, fecha_max], min_value=fecha_min, max_value=fecha_max)

# Filtro de Sector (particular, pami, obra social, etc.)
sectores = df['Sector'].dropna().unique().tolist()
sector_seleccionado = st.sidebar.multiselect("Sector", options=sectores, default=sectores)

# Aplicar filtros
if len(fechas_seleccionadas) == 2:
    mask = (df['Fecha'] >= fechas_seleccionadas[0]) & (df['Fecha'] <= fechas_seleccionadas[1]) & (df['Sector'].isin(sector_seleccionado))
    df_filtrado = df[mask]
else:
    df_filtrado = df[df['Sector'].isin(sector_seleccionado)]

# 4. Título Principal
st.title("📊 Análisis Operativo de Turnos")
st.markdown(f"**Sucursal:** {df_filtrado['Sucursal'].iloc[0] if not df_filtrado.empty else 'N/A'} | **Periodo:** {fechas_seleccionadas[0]} al {fechas_seleccionadas[-1] if len(fechas_seleccionadas)>1 else fechas_seleccionadas[0]}")
st.divider()

# 5. Cálculo de KPIs
if not df_filtrado.empty:
    total_turnos = len(df_filtrado)
    
    # Turnos no atendidos o cancelados
    abandonos = len(df_filtrado[df_filtrado['Estado'].isin(['NO ATENDIDO', 'CANCELADO'])])
    tasa_abandono = (abandonos / total_turnos) * 100 if total_turnos > 0 else 0
    
    tme = df_filtrado['Espera_Minutos'].mean()
    tma = df_filtrado['Atencion_Minutos'].mean()

    # Mostrar KPIs en 4 columnas
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Volumen Total", f"{total_turnos:,}".replace(',', '.'))
    col2.metric("Tasa de Abandono", f"{tasa_abandono:.1f} %", delta=f"{abandonos} turnos perdidos", delta_color="inverse")
    col3.metric("Tiempo Medio Espera (TME)", f"{tme:.1f} min")
    col4.metric("Tiempo Medio Atención (TMA)", f"{tma:.1f} min")
    
    st.divider()

    # 6. Gráficos Interactivos con Plotly
    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        st.subheader("Demanda por Hora del Día")
        demanda_hora = df_filtrado.groupby('Hora').size().reset_index(name='Cantidad')
        fig_demanda = px.bar(demanda_hora, x='Hora', y='Cantidad', 
                             labels={'Hora': 'Hora del Día', 'Cantidad': 'Turnos Emitidos'},
                             color_discrete_sequence=['#1f77b4'])
        fig_demanda.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=1))
        st.plotly_chart(fig_demanda, use_container_width=True)

    with row1_col2:
        st.subheader("Tiempo de Espera por Sector")
        espera_sector = df_filtrado.groupby('Sector')['Espera_Minutos'].mean().reset_index().sort_values(by='Espera_Minutos')
        fig_espera = px.bar(espera_sector, x='Espera_Minutos', y='Sector', orientation='h',
                            labels={'Espera_Minutos': 'Minutos Promedio', 'Sector': ''},
                            color='Espera_Minutos', color_continuous_scale='Reds')
        st.plotly_chart(fig_espera, use_container_width=True)

    st.divider()
    
    # 7. Vista de Rendimiento por Operador (Puesto.1)
    st.subheader("Rendimiento por Operador (Cajas)")
    
    # Filtrar solo los atendidos para evaluar a los cajeros
    df_atendidos = df_filtrado[df_filtrado['Estado'] == 'ATENDIDO']
    
    if not df_atendidos.empty and 'Puesto.1' in df_atendidos.columns:
        rendimiento_cajas = df_atendidos.groupby('Puesto.1').agg(
            Turnos_Atendidos=('Cód.', 'count'),
            TMA_Promedio=('Atencion_Minutos', 'mean')
        ).reset_index().sort_values(by='Turnos_Atendidos', ascending=False)
        
        fig_cajas = px.scatter(rendimiento_cajas, x='Turnos_Atendidos', y='TMA_Promedio', 
                               text='Puesto.1', size='Turnos_Atendidos', color='TMA_Promedio',
                               labels={'Turnos_Atendidos': 'Cantidad de Turnos Atendidos', 'TMA_Promedio': 'Tiempo de Atención Promedio (min)'},
                               color_continuous_scale='Viridis')
        fig_cajas.update_traces(textposition='top center')
        st.plotly_chart(fig_cajas, use_container_width=True)
    else:
        st.info("No hay datos suficientes de atención para mostrar el rendimiento por caja.")

else:
    st.warning("No hay datos para los filtros seleccionados.")
