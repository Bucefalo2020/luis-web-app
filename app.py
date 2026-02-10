import streamlit as st
import google.generativeai as genai
import os
from google.api_core import client_options

# 1. Configuración de página
st.set_page_config(page_title="Coach Luis - Zurich Santander", layout="wide")

# 2. Obtención de la llave
# Usamos el nuevo nombre para romper el cache de Railway
api_key_env = os.environ.get("GEMINI_API_KEY")

with st.sidebar:
    st.title("⚙️ Configuración")
    # Entrada manual por si Railway falla (Tu jerarquía de poder)
    api_key_input = st.text_input("Ingresa tu API Key (opcional)", type="password")
    modo = st.radio("Selecciona el Modo:", ["Taller", "Evaluador"])

# La variable final que usará la función
api_key_final = api_key_input if api_key_input else api_key_env

def llamar_a_luis(prompt_usuario, modo_seleccionado):
    if not api_key_final:
        return "⚠️ Error: No se encontró la API Key. Revisa que en Railway se llame GEMINI_API_KEY."
    
    try:
        # Forzamos la versión 1 estable de la API (Solución ChatGPT)
        options = client_options.ClientOptions(api_endpoint="generativelanguage.googleapis.com")
        genai.configure(api_key=api_key_final, client_options=options)
        
        # Seleccionamos el modelo gemini-1.5-flash
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        instruccion = (
            "Eres Luis, Coach experto de Zurich Santander México. "
            "Producto: Hogar Protegido 2020. Responde de forma amable y técnica."
        )
        
        # Llamada al modelo
        response = model.generate_content(f"{instruccion}\nModo: {modo_seleccionado}\nUsuario: {prompt_usuario}")
        return response.text

    except Exception as e:
        # Esto nos dará el detalle exacto si algo falla
        return f"❌ Detalle técnico: {str(e)}"

# 3. Interfaz de Chat
st.title("🛡️ Coach Luis")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "¡Hola! Soy Luis. ¿En qué puedo ayudarte hoy con Hogar Protegido?"}]

# Mostrar historial
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada de usuario
if prompt := st.chat_input("Escribe tu duda técnica aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Luis está consultando los manuales..."):
            respuesta = llamar_a_luis(prompt, modo)
            st.markdown(respuesta)
            st.session_state.messages.append({"role": "assistant", "content": respuesta})
