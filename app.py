import pandas as pd
import os

# Simulamos la ruta del archivo subido
ruta_archivo = "Turnos_ANT.xlsx - Sheet1.csv"
nombre_archivo = os.path.basename(ruta_archivo)

# Extraemos 'ANT' del nombre (asumiendo el formato Turnos_SUCURSAL)
sucursal = nombre_archivo.split('_')[1].split('.')[0] 

# Leemos el archivo
df = pd.read_csv(ruta_archivo)

# Agregamos la columna para mantener la jerarquía
df['Sucursal'] = sucursal
df['Empresa'] = 'Farmacia Central' # Ejemplo de nivel superior
df['Grupo_Empresarial'] = 'Grupo Salud' # Nivel máximo

# Limpieza de tiempos de espera para poder graficarlos (convertir a minutos)
df['Tiempo Espera (Min)'] = pd.to_timedelta(df['Tiempo Espera    ']).dt.total_seconds() / 60

print(df[['Cód.', 'Sucursal', 'Tiempo Espera (Min)']].head())
