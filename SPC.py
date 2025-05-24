# -*- coding: utf-8 -*-
"""
Created on Fri May 23 17:17:24 2025

@author: acer
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import requests

# Configuración de la app
st.set_page_config(
    page_title="Monitoreo de Métricas",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔁 CONFIGURACIÓN DE TELEGRAM
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

def generarAlerta(valorMedida, parMinMonitoreo, parMaxMonitoreo, maquina):
    if valorMedida < parMinMonitoreo:
        mensaje = f"🔴 *ALERTA:* Máquina {maquina} - Valor {valorMedida} < mínimo permitido {parMinMonitoreo}."
    elif valorMedida > parMaxMonitoreo:
        mensaje = f"🔴 *ALERTA:* Máquina {maquina} - Valor {valorMedida} > máximo permitido {parMaxMonitoreo}."
    else:
        return
    enviarMensajeTelegram(mensaje)

# Sidebar
with st.sidebar:
    parMinMonitoreo = st.number_input("Rango Mínimo", value=15)
    parMaxMonitoreo = st.number_input("Rango Máximo", value=27)
    parVentanaDatos = st.number_input("Ventana de Datos", value=15)
    parSegundosActualizacion = st.number_input("Segundos de Actualización", value=10)
    if st.button("Probar notificación"):
        enviarMensajeTelegram("✅ *Prueba de notificación desde Streamlit*")

st.header("📈 Monitoreo de Métricas por Máquina")

# Función para cargar datos
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
    st.stop()

# Inicializar estado por máquina
for maquina in maquinas_seleccionadas:
    if maquina not in st.session_state:
        st.session_state[maquina] = {'ultimaFecha': None, 'enAlerta': False}

# Función para mostrar cada fragmento de máquina de forma segura
def mostrar_maquina_fragment(maquina):
    @st.fragment(run_every=parSegundosActualizacion)
    def fragment():
        try:
            df = cargar_datos()
            df_maquina = df[df['Maquina'] == maquina].sort_values("FechaHora").tail(parVentanaDatos)
            if df_maquina.empty:
                st.warning(f"No hay datos recientes para la máquina {maquina}")
                return

            valorMedida = df_maquina['Medida'].iloc[-1]
            ultimaFecha = df_maquina['FechaHora'].iloc[-1]

            color = "green"
            if valorMedida < parMinMonitoreo or valorMedida > parMaxMonitoreo:
                color = "red"

            fig = px.line(df_maquina, x='FechaHora', y='Medida', markers=True)
            fig.update_traces(line=dict(color=color))
            fig.add_hrect(y0=parMinMonitoreo, y1=parMaxMonitoreo, fillcolor="#DAFFFB", opacity=0.5)
            fig.update_layout(title=f"Máquina: {maquina}")
            st.plotly_chart(fig, use_container_width=True)

            if ultimaFecha != st.session_state[maquina]['ultimaFecha']:
                st.session_state[maquina]['ultimaFecha'] = ultimaFecha
                if valorMedida < parMinMonitoreo or valorMedida > parMaxMonitoreo:
                    st.session_state[maquina]['enAlerta'] = True
                    generarAlerta(valorMedida, parMinMonitoreo, parMaxMonitoreo, maquina)
                else:
                    if st.session_state[maquina]['enAlerta']:
                        st.session_state[maquina]['enAlerta'] = False
                        mensaje = f"✅ *RESUELTA:* Máquina {maquina} volvió al rango normal ({valorMedida})."
                        enviarMensajeTelegram(mensaje)
        except Exception as e:
            st.error(f"Error en la máquina {maquina}: {e}")

    fragment()

# Mostrar fragmento por cada máquina seleccionada
for maquina in maquinas_seleccionadas:
    mostrar_maquina_fragment(maquina)





