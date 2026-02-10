import streamlit as st
import google.generativeai as genai
import os
from google.api_core import client_options

# 1. Configuración de página
st.set_page_config(page_title="Coach Luis - Zurich Santander", layout="wide")

def llamar_a_luis(prompt_usuario, modo_seleccionado, api_key_manual):
    # Cambiamos el nombre de la variable para romper el cache
    api_key_final = api_key_manual if api_key_manual else os.environ.get("GEMINI_API_KEY")

    if not api_key_final:
        return "⚠️ Error: No se encontró la API Key en Railway."
    
    try:
        # --- LA SOLUCIÓN DE CHATGPT APLICADA ---
        # Forzamos al cliente a usar la versión 1 estable de la API
        options = client_options.ClientOptions(api_endpoint="generativelanguage.googleapis.com")
        genai.configure(api_key=api_key_final, client_options=options)
        
        # Seleccionamos el modelo
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        instruccion = (
            "Eres Luis, Coach experto de Zurich Santander México. "
            "Producto: Hogar Protegido 2020. Responde de forma amable y técnica."
        )
        
        # Llamada al modelo
        response = model.generate_content(f"{instruccion}\nModo: {modo_seleccionado}\nUsuario: {prompt_usuario}")
        return response.text

    except Exception as e:
        return f"❌ Detalle técnico: {str(e)}"

# --- INTERFAZ ---
st.title("🛡️ Coach Luis")

with st.sidebar:
    st.title("⚙️ Configuración")
    key_input = st.text_input("API Key (opcional si está en Railway)", type="password")
    modo = st.radio("Modo:", ["Taller", "Evaluador"])

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "¡Hola! Soy Luis. ¿En qué puedo ayudarte hoy?"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Escribe tu duda técnica aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Luis está consultando los manuales..."):
            respuesta = llamar_a_luis(prompt, modo, key_input)
            st.markdown(respuesta)
            st.session_state.messages.append({"role": "assistant", "content": respuesta})
