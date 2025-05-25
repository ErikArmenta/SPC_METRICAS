# -*- coding: utf-8 -*-
"""
Created on Fri May 23 17:17:24 2025

@author: acer
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json # Asegúrate de que esta librería esté importada si la usas en la función enviarMensajeWhatsApp original

# Definimos los parámetros de configuración de la aplicación
st.set_page_config(
    page_title="Monitoreo de Metricas",  # Título de la página
    page_icon="📊",  # Ícono
    layout="wide",  # Forma de layout ancho o compacto
    initial_sidebar_state="expanded"  # Definimos si la barra lateral aparece expandida o colapsada
)

# 🔁 CONFIGURACIÓN DE TELEGRAM (manteniendo tu configuración actual)
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

# Modificación para aceptar 'id_inspector' (asumiendo que lo añadirás más tarde)
def generarAlerta(valorMedida, parMinMonitoreo, parMaxMonitoreo, maquina, id_inspector=None):
    mensaje_base = ""
    if id_inspector:
        mensaje_base = f"Inspector: {id_inspector} - " # Puedes añadirlo si tienes la columna

    if valorMedida < parMinMonitoreo:
        mensaje = f"🔴 *ALERTA:* {mensaje_base}Máquina {maquina} - Valor {valorMedida} < mínimo permitido {parMinMonitoreo}."
    elif valorMedida > parMaxMonitoreo:
        mensaje = f"🔴 *ALERTA:* {mensaje_base}Máquina {maquina} - Valor {valorMedida} > máximo permitido {parMaxMonitoreo}."
    else:
        return
    enviarMensajeTelegram(mensaje)

# Configuración de los parámetros en la barra lateral
with st.sidebar:
    parMinMonitoreo = st.number_input("Rango Minimo", value=15)
    parMaxMonitoreo = st.number_input("Rango Maximo", value=27)
    parVentanaDatos = st.number_input("Ventana de Datos", value=15)
    parSegundosActualizacion = st.number_input("Segundos de Actualización", value=10) # Sugerencia: 10 segundos para empezar
    if st.button("Probar notificación"):
        enviarMensajeTelegram("✅ *Prueba de notificación desde Streamlit*")

st.header("📈 Monitoreo de Métricas por Máquina")

# Función para cargar datos (se mantiene igual, asumiendo que el Google Sheet ya está público o usarás st.secrets)
@st.cache_data(ttl=30)
def cargar_datos():
    gsheetid = '1vlUJhaPlwdwKWe-U_rGr4BDf6kgLvxmL0nj2293a0Ok'
    sheetid = '0'
    url = f'https://docs.google.com/spreadsheets/d/{gsheetid}/export?format=csv&gid={sheetid}'
    df = pd.read_csv(url)
    df['FechaHora'] = pd.to_datetime(df['FechaHora'])
    return df

# Cargar datos y mostrar selector
try:
    df = cargar_datos()
    maquinas_disponibles = df['Maquina'].unique().tolist()
    maquinas_seleccionadas = st.multiselect("Seleccionar máquinas a visualizar", maquinas_disponibles, default=maquinas_disponibles[:1])
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.stop() # Detiene la ejecución si hay un error crítico al cargar datos

# Inicializar estado por máquina
for maquina in maquinas_seleccionadas:
    if maquina not in st.session_state:
        st.session_state[maquina] = {'ultimaFecha': None, 'enAlerta': False}

# Función para mostrar cada fragmento de máquina de forma segura
def mostrar_maquina_fragment(maquina):
    @st.fragment(run_every=parSegundosActualizacion)
    def fragment():
        try:
            df = cargar_datos() # Carga los datos de nuevo dentro del fragmento para asegurar que estén frescos
            df_maquina = df[df['Maquina'] == maquina].sort_values("FechaHora").tail(parVentanaDatos)
            
            if df_maquina.empty:
                st.warning(f"No hay datos recientes para la máquina {maquina}. Revisando...")
                return # Salir si no hay datos para evitar errores

            valorMedida = df_maquina['Medida'].iloc[-1]
            ultimaFecha = df_maquina['FechaHora'].iloc[-1]
            
            # Intenta obtener el ID del inspector si la columna existe
            id_inspector_actual = None
            if 'ID_Inspector' in df_maquina.columns and not df_maquina['ID_Inspector'].empty:
                id_inspector_actual = df_maquina['ID_Inspector'].iloc[-1]

            fig = px.line(df_maquina, x='FechaHora', y='Medida', markers=True)
            fig.add_hrect(y0=parMinMonitoreo, y1=parMaxMonitoreo, fillcolor="#DAFFFB", line_color="rgba(0,0,0,0)", opacity=0.5)
            fig.add_hline(y=parMinMonitoreo, line_dash="dot", annotation_text="Minimo", annotation_position="bottom right")
            fig.add_hline(y=parMaxMonitoreo, line_dash="dot", annotation_text="Maximo", annotation_position="bottom right")
            fig.update_yaxes(rangemode="tozero")
            fig.update_layout(title=f"Máquina: {maquina}")
            st.plotly_chart(fig, use_container_width=True)

            if ultimaFecha != st.session_state[maquina]['ultimaFecha']:
                st.session_state[maquina]['ultimaFecha'] = ultimaFecha
                if valorMedida < parMinMonitoreo or valorMedida > parMaxMonitoreo:
                    st.session_state[maquina]['enAlerta'] = True
                    generarAlerta(valorMedida, parMinMonitoreo, parMaxMonitoreo, maquina, id_inspector_actual)
                else:
                    if st.session_state[maquina]['enAlerta']:
                        st.session_state[maquina]['enAlerta'] = False
                        mensaje_resolucion_base = ""
                        if id_inspector_actual:
                            mensaje_resolucion_base = f"Inspector: {id_inspector_actual} - "
                        mensaje = f"✅ *RESUELTA:* {mensaje_resolucion_base}Máquina {maquina} volvió al rango normal ({valorMedida})."
                        enviarMensajeTelegram(mensaje)
        except Exception as e:
            # Aquí podrías capturar errores específicos de Plotly o Pandas si fuera necesario
            st.error(f"Error en la máquina {maquina} al actualizar o renderizar: {e}")
            # Puedes imprimir el traceback completo para depuración
            # import traceback
            # st.error(traceback.format_exc())

    fragment() # Llamar a la función fragment para que se ejecute

# Mostrar fragmento por cada máquina seleccionada
# Importante: Asegúrate de que esta iteración no genere elementos duplicados o conflictos.
# Cada fragment() se encarga de su propio espacio.
for maquina in maquinas_seleccionadas:
    mostrar_maquina_fragment(maquina)





