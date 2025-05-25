# -*- coding: utf-8 -*-
"""
Created on Fri May 23 17:17:24 2025

@author: acer
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json 

# --- CONFIGURACIÓN GENERAL DE LA APLICACIÓN ---
st.set_page_config(
    page_title="Monitoreo de Metricas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONFIGURACIÓN DE TELEGRAM ---
TELEGRAM_CHAT_ID = "5894806227"
TELEGRAM_BOT_TOKEN = "7776201055:AAHRVm4d7y04B2eQLM0QUT6lYbWLBrtOZIw"

def enviarMensajeTelegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        st.error(f"Error al enviar mensaje de Telegram: {e}")

def generarAlerta(valorMedida, parMinMonitoreo, parMaxMonitoreo, maquina, id_inspector=None):
    mensaje_base = ""
    if id_inspector:
        mensaje_base = f"Inspector: {id_inspector} - "

    if valorMedida < parMinMonitoreo:
        mensaje = f"🔴 *ALERTA:* {mensaje_base}Máquina {maquina} - Valor {valorMedida} < mínimo permitido {parMinMonitoreo}."
    elif valorMedida > parMaxMonitoreo:
        mensaje = f"🔴 *ALERTA:* {mensaje_base}Máquina {maquina} - Valor {valorMedida} > máximo permitido {parMaxMonitoreo}."
    else:
        return
    enviarMensajeTelegram(mensaje)

# --- CONFIGURACIÓN DE PARÁMETROS EN LA BARRA LATERAL ---
with st.sidebar:
    parMinMonitoreo = st.number_input("Rango Minimo", value=15)
    parMaxMonitoreo = st.number_input("Rango Maximo", value=27)
    parVentanaDatos = st.number_input("Ventana de Datos", value=15)
    # Aumenta el tiempo de actualización para depurar si el error persiste
    parSegundosActualizacion = st.number_input("Segundos de Actualización", value=15) 
    if st.button("Probar notificación"):
        enviarMensajeTelegram("✅ *Prueba de notificación desde Streamlit*")

st.header("📈 Monitoreo de Métricas por Máquina")

# --- FUNCIÓN PARA CARGAR DATOS (con caché) ---
@st.cache_data(ttl=30)
def cargar_datos():
    gsheetid = '1vlUJhaPlwdwKWe-U_rGr4BDf6kgLvxmL0nj2293a0Ok'
    sheetid = '0'
    url = f'https://docs.google.com/spreadsheets/d/{gsheetid}/export?format=csv&gid={sheetid}'
    try:
        df = pd.read_csv(url)
        df['FechaHora'] = pd.to_datetime(df['FechaHora'])
        return df
    except Exception as e:
        st.error(f"Error al cargar datos desde Google Sheets: {e}")
        return pd.DataFrame() 

# --- LÓGICA PRINCIPAL DE LA APLICACIÓN ---
try:
    df_completo = cargar_datos()
    # Ahora, maquinas_seleccionadas incluirá todas las máquinas disponibles automáticamente
    if not df_completo.empty and 'Maquina' in df_completo.columns:
        maquinas_seleccionadas = df_completo['Maquina'].unique().tolist()
    else:
        maquinas_seleccionadas = [] # No hay máquinas disponibles si el DF está vacío o no tiene la columna

except Exception as e:
    st.error(f"Error inicial al obtener lista de máquinas: {e}")
    st.stop()

# Inicializar estado para cada máquina seleccionada
for maquina in maquinas_seleccionadas:
    if maquina not in st.session_state:
        st.session_state[maquina] = {'ultimaFecha': None, 'enAlerta': False}

# --- UN ÚNICO FRAGMENTO GLOBAL PARA ACTUALIZAR TODAS LAS GRÁFICAS ---
@st.fragment(run_every=parSegundosActualizacion)
def actualizar_todas_las_maquinas(maquinas_a_mostrar, min_monitoreo, max_monitoreo, ventana_datos):
    df_actualizado = cargar_datos() # Cargar los datos una sola vez para este ciclo de actualización

    # Define el número de columnas para las gráficas
    num_columns = 2 
    
    cols = st.columns(num_columns) 
    col_idx = 0 

    for maquina in maquinas_a_mostrar:
        with cols[col_idx]: 
            try:
                df_maquina = df_actualizado[df_actualizado['Maquina'] == maquina].sort_values("FechaHora").tail(ventana_datos)
                
                if df_maquina.empty:
                    st.warning(f"No hay datos recientes para la máquina {maquina}. Revisando...")
                else: 
                    valorMedida = df_maquina['Medida'].iloc[-1]
                    ultimaFecha = df_maquina['FechaHora'].iloc[-1]
                    
                    id_inspector_actual = None
                    if 'ID_Inspector' in df_maquina.columns and not df_maquina['ID_Inspector'].empty:
                        id_inspector_actual = df_maquina['ID_Inspector'].iloc[-1]

                    # Dibujar la gráfica
                    fig = px.line(df_maquina, x='FechaHora', y='Medida', markers=True)
                    fig.add_hrect(y0=min_monitoreo, y1=max_monitoreo, fillcolor="#DAFFFB", line_color="rgba(0,0,0,0)", opacity=0.5)
                    fig.add_hline(y=min_monitoreo, line_dash="dot", annotation_text="Minimo", annotation_position="bottom right")
                    fig.add_hline(y=max_monitoreo, line_dash="dot", annotation_text="Maximo", annotation_position="bottom right")
                    fig.update_yaxes(rangemode="tozero")
                    fig.update_layout(title=f"Máquina: {maquina}", height=350) 
                    st.plotly_chart(fig, use_container_width=True)

                    # Lógica de alertas (solo si la fecha es nueva)
                    if ultimaFecha != st.session_state[maquina]['ultimaFecha']:
                        st.session_state[maquina]['ultimaFecha'] = ultimaFecha
                        if valorMedida < min_monitoreo or valorMedida > max_monitoreo:
                            st.session_state[maquina]['enAlerta'] = True
                            generarAlerta(valorMedida, min_monitoreo, max_monitoreo, maquina, id_inspector_actual)
                        else:
                            if st.session_state[maquina]['enAlerta']:
                                st.session_state[maquina]['enAlerta'] = False
                                mensaje_resolucion_base = ""
                                if id_inspector_actual:
                                    mensaje_resolucion_base = f"Inspector: {id_inspector_actual} - "
                                mensaje = f"✅ *RESUELTA:* {mensaje_resolucion_base}Máquina {maquina} volvió al rango normal ({valorMedida})."
                                enviarMensajeTelegram(mensaje)
            
            except Exception as e:
                st.error(f"Error al procesar la máquina {maquina} durante el renderizado/actualización: {e}")
        
        col_idx = (col_idx + 1) % num_columns 
        
# --- Llamada final al fragmento principal para que se ejecute ---
if maquinas_seleccionadas: 
    actualizar_todas_las_maquinas(
        maquinas_seleccionadas, 
        parMinMonitoreo, 
        parMaxMonitoreo, 
        parVentanaDatos
    )
else:
    st.info("No se encontraron máquinas para monitorear en la hoja de cálculo.")





